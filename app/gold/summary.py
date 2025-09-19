import json

def summarize(path="data/gold/results.jsonl"):
    scores, len_ok, cite_ok = [], 0, 0
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            scores.append(obj["score"])
            len_ok += obj["length_ok"]
            cite_ok += obj["citation_ok"]
    n = len(scores)
    print(f"Items: {n}")
    print(f"Avg score: {sum(scores)/n:.2f}")
    print(f"Length OK: {len_ok}/{n}")
    print(f"Citation OK: {cite_ok}/{n}")

if __name__ == "__main__":
    summarize()

