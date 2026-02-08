# PROJECT CONTEXT — DO NOT DEVIATE

## Project Name
AvatarAI Vision-Based Game Agent

## Goal
Create an AI agent that reacts to what is happening on screen (pixels only),
understands game state via vision, and plays games such as Pokémon Red in real time.

## Hard Constraints (DO NOT BREAK)
- Visual input only (screen capture)
- No emulator memory access
- Real-time reaction
- Python-based core
- Modular architecture (vision / decision / action)

## Current Decisions (LOCKED)
- Vision: Object detection + UI state recognition
- Decision: Hybrid system (rules + RL later)
- Input: Keyboard/controller emulation
- Emulator-based gameplay

## Out of Scope (for now)
- End-to-end large multimodal models
- Game memory hacking
- Cloud inference

## Style Guidelines
- Prefer simple, debuggable solutions
- No overengineering
- No speculative refactors

## Current Status
Planning phase. No code finalized yet.
