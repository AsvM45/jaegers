---
title: Wacky Wheels Control Tower
emoji: 🚚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: AI operations control tower for supply-chain incidents
---

# Wacky Wheels Control Tower

An AI operations control tower built for the Hitachi "Hack the Highway" datathon. A local language model
(qwen3:1.7b, through Ollama) reads supplier, plant and dealer messages; code checks every reading against
the company records; specialist agents reschedule production, notify dealers and assign loaners, and anything
unclear goes to a person.

Open the app at the direct link (`https://<user>-<space>.hf.space`) to sign in with the shared password.
