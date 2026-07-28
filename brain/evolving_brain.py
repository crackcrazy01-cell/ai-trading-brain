"""🧠 Evolving AI Brain — 50-neuron neural network (numpy-free, pure Python)"""
import math
import random
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def random_gauss(mu=0, sigma=1):
    u1 = random.random()
    u2 = random.random()
    return mu + sigma * math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(2 * math.pi * u2)

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

class Neuron:
    def __init__(self, weights=None, bias=None):
        self.weights = weights or [random_gauss(0, 0.5) for _ in range(20)]
        self.bias = bias if bias is not None else random_gauss(0, 0.5)
        self.strength = 0.5
        self.wins = 0
        self.losses = 0
        self.last_signal = None
    
    def forward(self, inputs):
        z = dot(self.weights, inputs) + self.bias
        self.last_signal = sigmoid(z)
        return self.last_signal
    
    def learn(self, inputs, target, alpha=0.1):
        pred = self.forward(inputs)
        error = target - pred
        for i in range(20):
            self.weights[i] += alpha * error * inputs[i]
        self.bias += alpha * error
    
    def to_dict(self):
        return {
            'weights': [round(w, 6) for w in self.weights],
            'bias': round(self.bias, 6),
            'strength': self.strength,
            'wins': self.wins,
            'losses': self.losses
        }
    
    @classmethod
    def from_dict(cls, d):
        n = cls(d['weights'], d['bias'])
        n.strength = d.get('strength', 0.5)
        n.wins = d.get('wins', 0)
        n.losses = d.get('losses', 0)
        return n


class EvolvingBrain:
    NUM_NEURONS = 50
    INPUT_FEATURES = 20
    BUY_THRESHOLD = 0.65
    SELL_THRESHOLD = 0.35
    
    def __init__(self):
        self.neurons = [Neuron() for _ in range(self.NUM_NEURONS)]
        self.generation = 0
        self.performance = 0.0
        self.confidence = 0.5
        self.evolution_log = []
        self.created_at = datetime.utcnow().isoformat()
        self.load()
    
    def decide(self, features):
        buy_votes = 0
        sell_votes = 0
        total_confidence = 0
        
        for neuron in self.neurons:
            output = neuron.forward(features)
            total_confidence += abs(output - 0.5)
            if output > self.BUY_THRESHOLD:
                buy_votes += 1
            elif output < self.SELL_THRESHOLD:
                sell_votes += 1
        
        confidence = (total_confidence / self.NUM_NEURONS) * 2
        
        if buy_votes > sell_votes:
            signal = 'buy'
        elif sell_votes > buy_votes:
            signal = 'sell'
        else:
            signal = 'hold'
        
        return {
            'signal': signal,
            'confidence': round(confidence, 3),
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'hold_votes': self.NUM_NEURONS - buy_votes - sell_votes
        }
    
    def reinforce(self, features, reward):
        alpha = 0.05
        for neuron in self.neurons:
            target = 0.9 if (neuron.last_signal or 0.5) > 0.5 else 0.1
            if reward < 0:
                target = 1 - target
            neuron.learn(features, target, alpha)
            
            if reward > 0:
                neuron.wins += 1
            else:
                neuron.losses += 1
            
            total = neuron.wins + neuron.losses
            neuron.strength = neuron.wins / total if total > 0 else 0.5
            neuron.strength = max(0.2, min(1.0, neuron.strength))
        
        self.save()
    
    def evolve(self):
        self.neurons.sort(key=lambda n: n.strength, reverse=True)
        cutoff = int(self.NUM_NEURONS * 0.4)
        survivors = self.neurons[:self.NUM_NEURONS - cutoff]
        
        new_neurons = []
        for i in range(cutoff):
            parent = survivors[i % len(survivors)]
            child = Neuron(
                weights=[w + random_gauss(0, 0.15) for w in parent.weights],
                bias=parent.bias + random_gauss(0, 0.15)
            )
            child.strength = parent.strength * 0.8
            new_neurons.append(child)
        
        self.neurons = survivors + new_neurons
        self.generation += 1
        
        log_entry = {
            'time': datetime.utcnow().isoformat(),
            'message': f'🧬 Evolution #{self.generation}: killed {cutoff} weak neurons, bred {cutoff} from top {len(survivors)}'
        }
        self.evolution_log.append(log_entry)
        if len(self.evolution_log) > 100:
            self.evolution_log = self.evolution_log[-100:]
        
        self.save()
        return log_entry
    
    def get_health(self):
        alive = sum(1 for n in self.neurons if n.strength > 0.3)
        avg_strength = sum(n.strength for n in self.neurons) / self.NUM_NEURONS
        return {
            'neurons_total': self.NUM_NEURONS,
            'neurons_alive': alive,
            'generation': self.generation,
            'confidence': round(self.confidence, 2),
            'performance': round(self.performance, 2),
            'avg_strength': round(avg_strength, 2),
            'neurons': sorted([{
                'strength': round(n.strength, 2),
                'wins': n.wins,
                'losses': n.losses
            } for n in self.neurons], key=lambda x: x['strength'], reverse=True)
        }
    
    def save(self):
        path = os.path.join(DATA_DIR, 'brain.json')
        data = {
            'neurons': [n.to_dict() for n in self.neurons],
            'generation': self.generation,
            'performance': self.performance,
            'confidence': self.confidence,
            'evolution_log': self.evolution_log,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow().isoformat()
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self):
        path = os.path.join(DATA_DIR, 'brain.json')
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self.neurons = [Neuron.from_dict(n) for n in data.get('neurons', [])]
                if len(self.neurons) != self.NUM_NEURONS:
                    self.neurons = [Neuron() for _ in range(self.NUM_NEURONS)]
                self.generation = data.get('generation', 0)
                self.performance = data.get('performance', 0)
                self.confidence = data.get('confidence', 0.5)
                self.evolution_log = data.get('evolution_log', [])
                self.created_at = data.get('created_at', datetime.utcnow().isoformat())
            except:
                pass

