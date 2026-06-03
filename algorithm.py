import json, os, random
import pandas as pd

SCORES_FILE = "scores.json"

#Vocabulary

def load_vocab(csv_path):
    df = pd.read_csv(csv_path, encoding="utf-8", header=None)
    hanzi_col, pinyin_col, english_col = 0, 1, 2
    vocab = []
    for _, row in df.iterrows():
        hanzi = str(row[hanzi_col]).strip()
        if not hanzi or hanzi.lower() in ("hanzi", "word", "chinese", "nan"):
            continue
        vocab.append({
            "hanzi":   hanzi,
            "pinyin":  str(row[pinyin_col]).strip(),
            "english": str(row[english_col]).strip(),
        })
    return vocab

#Scores

def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_scores(scores):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def update_score(scores, hanzi, correct):
    if hanzi not in scores:
        scores[hanzi] = {"correct": 0, "attempts": 0}
    scores[hanzi]["attempts"] += 1
    if correct:
        scores[hanzi]["correct"] += 1
    return scores

#Algorithm

def compute_weakness(correct, attempts):
    if attempts == 0:
        return 0.5
    return round((1 - correct / attempts) * (1 + attempts * 0.1), 4)

def get_weighted_words(vocab, scores, n=10):
    weights = [
        max(compute_weakness(
            scores.get(w["hanzi"], {}).get("correct", 0),
            scores.get(w["hanzi"], {}).get("attempts", 0)
        ), 0.01)
        for w in vocab
    ]
    selected, seen, safety = [], set(), n * 10
    while len(selected) < min(n, len(vocab)) and safety > 0:
        pick = random.choices(vocab, weights=weights, k=1)[0]
        if pick["hanzi"] not in seen:
            selected.append(pick)
            seen.add(pick["hanzi"])
        safety -= 1
    return selected

def get_boss_words(vocab, scores, count=10):
    return sorted(
        vocab,
        key=lambda w: compute_weakness(
            scores.get(w["hanzi"], {}).get("correct", 0),
            scores.get(w["hanzi"], {}).get("attempts", 0),
        ),
        reverse=True,
    )[:count]

#Stats

def get_stats_table(vocab, scores):
    rows = []
    for w in vocab:
        entry    = scores.get(w["hanzi"], {})
        correct  = entry.get("correct", 0)
        attempts = entry.get("attempts", 0)
        rate     = round(correct / attempts * 100, 1) if attempts else None
        rows.append({
            "Word":      w["hanzi"],
            "Pinyin":    w["pinyin"],
            "English":   w["english"],
            "Attempts":  attempts,
            "Correct %": f"{rate}%" if rate is not None else "—",
            "Weakness":  compute_weakness(correct, attempts),
        })
    return pd.DataFrame(rows).sort_values("Weakness", ascending=False)
