---
title: Wacky Wheels Control Tower
emoji: 🚚
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.32.0
app_file: app.py
pinned: false
short_description: AI operations control tower for supply-chain incidents
---

# Wacky Wheels Control Tower

An AI operations control tower built for the Hitachi "Hack the Highway" datathon. A small language model
(Qwen3 1.7B, running inside the Space with llama.cpp) reads supplier, plant and dealer messages; code checks every reading against
the company records; specialist agents reschedule production, notify dealers and assign loaners, and anything
unclear goes to a person.

Open the app at the direct link (`https://<user>-<space>.hf.space`) to sign in with the shared password.
