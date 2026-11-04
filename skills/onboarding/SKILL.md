---
name: onboarding
description: First-time setup for batch inference. Finds local model servers, records the user's backends (Ollama, llama.cpp, vLLM, LM Studio, their own servers, cloud APIs), and takes their guide to when each should be used, plus spend rules, secrets wrapper and notebook location. Rerun to change any of it. Use for "onboarding", "set up batch inference", "add my Ollama server", "add a backend", "change when we use local models".
---

# Onboarding

The goal is a guide the router can follow without asking again: which backends exist, and when each one is
right. The rules are the user's, so ask for them and write them down in their words. Don't invent policy.

Data directory: `scripts/paths.sh dir`. Two files go there, and neither belongs in a repo that's public:

- `backends.json`: connection facts (format: `shared/backends.example.json`). **Never a key**, only `api_key_env`.
- `defaults.md`: the guide and everything else (format: `shared/defaults.example.md`).

If they exist, read them first and change only what the user wants changed. Show what you'd keep.

## 1. Look before asking

```bash
python3 scripts/backends.py discover                  # local servers on the usual ports
python3 scripts/backends.py check                     # anything already configured
command -v ollama llama-server vllm lms
env | cut -d= -f1 | grep -E 'OPENROUTER|ANTHROPIC|DEEPSEEK|OPENAI'
```

Report what you found, as names only.

## 2. Ask, a few questions at a time

**Backends**
- Which machines or servers run models beyond what was found? Get type, URL, whether a key is needed, and the name of
  the variable holding it. A server on another machine must be reachable: Ollama binds to localhost unless
  `OLLAMA_HOST` says otherwise.
- For each: its default model, how many requests it can take at once (1 for most single-GPU Ollama setups), and
  when it's available (always on, or has to be woken).
- Which cloud routes do they use: Anthropic, OpenRouter, others?

**When to use which.** This is the heart of it. Offer these prompts, and take the answers as given:
- Is there data that must never leave their machines? How would an agent recognise it?
- When is a slow free run better than a fast cheap paid one? Is there a size where local stops being worth it?
- Which kinds of job are local models good enough for, in their experience, and which never?
- What's the default when nothing else applies?
- Are any backends off limits for batch work, such as a server busy with something else?

**The rest**
- Spend: when to ask before a run, and any hard ceiling.
- Secrets: do keys sit in the environment, or does a wrapper need to go before each command?
- Notebook: where should dated prices and run records live? The default is inside the data directory.

## 3. Write

`backends.json`, then `defaults.md` with a `## When to use which backend` section: one row per rule, in order, first
match wins, ending in the default.

## 4. Verify

```bash
python3 scripts/backends.py check
python3 scripts/backends.py speed <name> --model <model> --items 1000 --out-per-item 150
```

Add the measured speed to the backend's `notes` with today's date: routing needs it to weigh hours against dollars. A
backend that's down isn't a failed onboarding if it's a machine that sleeps. Say so, and leave it in.

Finish by running one sample job past the guide: "for 5,000 private emails I'd use X, because rule 1". Ask if that's right.
