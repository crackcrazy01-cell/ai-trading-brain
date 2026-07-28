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
