from app.hrm.pipeline import run
import sys, json

def main():
    goal = sys.argv[1] if len(sys.argv) > 1 else "today AI research news"
    r = run(goal)
    print("PLAN:", r["steps"])
    print("SCORE:", round(r["judge"]["score"], 3), "| len_ok:", r["judge"]["length_ok"], "| cite_ok:", r["judge"]["citation_ok"])
    print("NOTES:", r["judge"]["rubric_notes"])
    print("CITATIONS:", r["out"]["citations"])
    print("\n--- ANSWER ---\n", r["out"]["answer"])
    # Optional JSON dump for CI
    # print(json.dumps(r, indent=2))

if __name__ == "__main__":
    main()

