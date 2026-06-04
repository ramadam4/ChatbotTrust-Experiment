# The Influence of Personalization and Conversation Warmth on User Risk Perception and Trust in AI-Driven Chatbots: A Cross-Domain Experimental Study
---

## Study Overview

This study investigates whether chatbot personalization and conversation warmth jointly shape user trust through risk perception, and whether these effects are moderated by domain context. Participants interact with an AI advisory chatbot embedded in a Qualtrics survey and then report their risk perception and trust.

The experiment uses a **2 (Personalization: high vs. low) × 2 (Warmth: warm vs. cold) × 2 (Domain: financial advisory vs. retail recommendation) fully crossed between-subjects design**, yielding 8 experimental conditions.

| Condition | Personalization | Warmth | Domain |
|-----------|-----------------|--------|--------|
| C1 | High | Warm | Financial Advisory |
| C2 | High | Warm | Retail Recommendation |
| C3 | High | Cold | Financial Advisory |
| C4 | High | Cold | Retail Recommendation |
| C5 | Low  | Warm | Financial Advisory |
| C6 | Low  | Warm | Retail Recommendation |
| C7 | Low  | Cold | Financial Advisory |
| C8 | Low  | Cold | Retail Recommendation |

Target N = 600 (approx. 75 per condition), recruited via Prolific Academic.

---

## Hypotheses

| Hypothesis | Relationship | Predicted direction |
|------------|--------------|---------------------|
| H1a | Personalization → Risk Perception | Higher personalization → lower risk perception |
| H1b | Personalization → Trust | Higher personalization → higher trust |
| H2a | Warmth → Risk Perception | Warm style → lower risk perception |
| H2b | Warmth → Trust | Warm style → higher trust |
| H3  | Personalization × Warmth → Risk Perception | Combined effect exceeds additive prediction |
| H4a | Personalization → RP → Trust | RP mediates the personalization–trust link |
| H4b | Warmth → RP → Trust | RP mediates the warmth–trust link |
| H5a | Domain × Personalization → RP | Personalization effect stronger in financial domain |
| H5b | Domain × Warmth → RP | Warmth effect stronger in financial domain |
| H6a | Domain-moderated indirect effect (personalization) | Indirect effect stronger in financial domain |
| H6b | Domain-moderated indirect effect (warmth) | Indirect effect stronger in financial domain |

---

## Key Outcome Measures

- **Risk Perception** (mediator): 12-item scale across four dimensions — financial, performance, psychological, and privacy risk. Higher scores = higher perceived risk.
- **Trust** (dependent variable): 6-item scale covering cognitive and emotional trust. Higher scores = higher trust.

---

## Chatbot Domains

### Financial Advisory — FinanceWise
Participants receive investment portfolio advice based on their stated investment goal, risk tolerance, and time horizon. High-personalization responses explicitly reference these inputs. Low-personalization responses give generic portfolio guidance.

### Retail Recommendation — ShopGuide
Participants receive smartphone recommendations based on their stated primary use case, budget range, and feature priorities. High-personalization responses explicitly reference these inputs. Low-personalization responses give a generic balanced recommendation.

---

## Chatbot URL Parameters

The Gradio chatbot app (`app.py`) is embedded as an iframe in Qualtrics. Condition assignment is passed via URL query parameters.

| Parameter | Values | Description |
|-----------|--------|-------------|
| `pid` | Qualtrics response ID | Participant identifier for logging |
| `domain` | `financial` / `retail` | Domain condition |
| `warmth` | `0` / `1` | 0 = cold, 1 = warm |
| `investment_goal` | user's text input | Financial domain, high personalization only |
| `risk_tolerance` | `conservative` / `moderate` / `aggressive` | Financial domain, high personalization only |
| `time_horizon` | `short` / `medium` / `long` | Financial domain, high personalization only |
| `use_case` | user's text input | Retail domain, high personalization only |
| `budget` | `under300` / `300to600` / `over600` | Retail domain, high personalization only |
| `features` | user's text input | Retail domain, high personalization only |

**Low personalization conditions:** omit the profile parameters (investment_goal/risk_tolerance/time_horizon or use_case/budget/features) from the URL. The chatbot falls back to generic responses automatically.

**Example URL (Financial, Warm, High Personalization):**
```
https://your-app-url.com/?pid=${e://Field/ResponseID}&domain=financial&warmth=1&investment_goal=${q://QID5/ChoiceTextEntryValue}&risk_tolerance=${q://QID6/ChoiceDescription}&time_horizon=${q://QID7/ChoiceDescription}
