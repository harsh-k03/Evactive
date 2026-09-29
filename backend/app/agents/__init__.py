"""Multi-agent layer. Order matters: sense -> assess -> decide -> route | (people move) | account -> communicate."""
from .accountability import AccountabilityAgent
from .assessment import AssessmentAgent
from .commander import CommanderAgent
from .comms import CommsAgent
from .detection import DetectionAgent
from .routing_agent import RoutingAgent


def build_agents(engine):
    return {
        "pre": [DetectionAgent(engine), AssessmentAgent(engine), CommanderAgent(engine), RoutingAgent(engine)],
        "post": [AccountabilityAgent(engine), CommsAgent(engine)],
    }
