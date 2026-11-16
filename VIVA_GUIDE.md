# Viva & Presentation Guide

## 5-minute demo script
1. **Problem (30 s):** lost items get buried in WhatsApp groups; goal = reunite owner and item faster.
2. **Show `python demo.py` (2 min).** Point at the ACTION line each time: WAIT -> NOTIFY -> ASK -> NOTIFY -> reject -> re-link -> confirm.
3. **Show the "why" line** (`text=0.51, category=1.00 ...`): the agent can explain its decisions.
4. **Show results (1 min):** open `results/evaluation_results.txt`: agent 0.71 top-1 vs 0.25 / 0.37 baselines.
5. **Limitations (30 s):** synthetic data, text only, cautious by design.

## Likely questions and short answers
1. **Why is this an agent, not a search?** It senses (reads reports), keeps state (database), decides (NOTIFY/ASK/WAIT) and acts (notifies, asks, re-checks) without being told to; a search box only answers when asked.
2. **Which agent type?** Goal-based (goal: reunite item and owner) with a utility function (the match score). Not simple-reflex, because it uses memory and compares options; not learning, because the weights are set by hand (learning is future work).
3. **Explain PEAS.** P: match accuracy, false alarms, questions asked. E: campus, lost/found reports, users, security desk. A: notify, ask, rank, store, flag for review. S: text description, place, time, user answers.
4. **Environment properties?** Partially observable (descriptions are incomplete), stochastic (people describe things differently), dynamic (reports keep arriving), sequential, discrete, multi-agent (owners, finders, desk, cooperative).
5. **Autonomous or semi-autonomous?** Semi: the agent acts alone up to the suggestion, but a human confirms the hand-over, because a wrong hand-over has real cost.
6. **How is the score computed?** Weighted sum of six clues (text 0.25, category 0.15, colour 0.20, brand 0.05, location 0.15, time 0.20). Unknown clue = 0.5. Different categories multiply by 0.4.
7. **What is TF-IDF?** Each word gets a weight: rare, informative words ("sticker") count more than common ones. A description becomes a vector; cosine similarity says how alike two vectors are.
8. **Why not deep learning?** Small data, needs to be explainable, runs on any laptop. TF-IDF + rules gives readable reasons for each decision. Embeddings/photo models are listed as extensions.
9. **How did you choose thresholds?** Grid search on one dev set (seed 1), then reported on five other sets (seeds 2-6) to avoid fooling ourselves.
10. **Why does it ask questions?** If 0.45 <= score < 0.75, or the top two candidates are within 0.15, it is not sure. It asks about the most useful missing clue (colour, brand, place, unique mark) and re-thinks. This raises automatic resolution from 22% to 38% in our simulation.
11. **What if the score is wrong?** NOTIFY only reserves the pair; the security desk can REJECT. Rejected pairs are stored and never suggested again.
12. **Fraud / privacy?** Questions never reveal the other report's details; the desk checks proof of ownership.
13. **What are the weaknesses?** Synthetic test data; text-only; vocabulary is hand-written, so unknown words (e.g. "earpods") lose information; 60% of cases still need human review.
14. **Baselines?** Plain TF-IDF (0.25 top-1) and TF-IDF with synonyms (0.37). Adding category/colour/place/time clues gets 0.71.
15. **How would you improve it?** Sentence embeddings, photo matching, learn the weights from confirmed matches, real SMS/e-mail, web UI.

## Rubric checklist (50 marks)
| Criteria | Evidence in this project |
|---|---|
| Problem identification (5) | Report section 1: real problem + measurable objectives O1-O5, checked against results |
| Agent design (10) | PEAS table, agent type justification, environment properties, architecture and decision policy |
| Implementation (15) | Working agent (`agent.py`), 13 unit tests, CLI, SQLite memory, evaluation with baselines |
| Documentation (10) | Project report + README + this guide + results file |
| Presentation & viva (10) | `demo.py` for a live demo + the Q&A above |
