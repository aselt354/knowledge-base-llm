import matplotlib.pyplot as plt
import matplotlib
import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(exist_ok=True)

matplotlib.rcParams['font.family'] = 'DejaVu Sans'


def get_latest_json():
    files = list(RESULTS_DIR.glob("results_*.json"))
    if not files:
        raise FileNotFoundError("Нет результатов в папке results/")

    return max(files, key=lambda f: f.stat().st_mtime)


def plot_all(json_filename=None):

    # ✔️ если ничего не передали — берём последний файл
    if json_filename is None:
        json_path = get_latest_json()
    else:
        json_path = RESULTS_DIR / json_filename

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_cat = data["by_category"]
    totals = data["totals"]

    cat_names_map = {
        "всегда наблюдается":  "Всегда\nнаблюдается",
        "может наблюдаться":   "Может\nнаблюдаться",
        "всегда отсутствует":  "Всегда\nотсутствует",
        "может отсутствовать": "Может\nотсутствовать",
    }

    cat_names, step1_vals, step2_vals = [], [], []

    for key in ["всегда наблюдается", "может наблюдаться",
                "всегда отсутствует", "может отсутствовать"]:
        if key in by_cat:
            cat_names.append(cat_names_map[key])
            step1_vals.append(by_cat[key]["step1_acc"])
            step2_vals.append(by_cat[key]["step2_acc"])

    # --------------------------------------------------------
    # ГРАФИК 1 — точность по категориям
    # --------------------------------------------------------

    x = np.arange(len(cat_names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    bars1 = ax.bar(x - width/2, step1_vals, width,
                   label='Шаг 1: тип связи', alpha=0.9)

    bars2 = ax.bar(x + width/2, step2_vals, width,
                   label='Шаг 2: уточнение', alpha=0.9)

    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1.5,
                    f'{h:.0f}%', ha='center', va='bottom')

    for bar in bars2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1.5,
                    f'{h:.0f}%', ha='center', va='bottom')

    ax.set_title("Точность по категориям")
    ax.set_ylabel("Точность (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(cat_names)
    ax.set_ylim(0, 120)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    graph1_path = RESULTS_DIR / "graph1_by_category.png"
    plt.savefig(graph1_path, dpi=150, bbox_inches='tight')
    plt.show()

    print("Сохранён:", graph1_path)

    # --------------------------------------------------------
    # ГРАФИК 2 — направления
    # --------------------------------------------------------

    directions = ['Прямое', 'Обратное']

    step1_dir = [totals["step1_acc"], totals.get("rev_step1_acc", 0)]
    step2_dir = [totals["step2_acc"], totals.get("rev_step2_acc", 0)]

    x2 = np.arange(len(directions))

    fig2, ax2 = plt.subplots(figsize=(8, 6))

    ax2.bar(x2 - width/2, step1_dir, width, label='Шаг 1')
    ax2.bar(x2 + width/2, step2_dir, width, label='Шаг 2')

    ax2.set_title("Точность по направлениям")
    ax2.set_ylabel("Точность (%)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(directions)
    ax2.set_ylim(0, 120)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()

    graph2_path = RESULTS_DIR / "graph2_directions.png"
    plt.savefig(graph2_path, dpi=150, bbox_inches='tight')
    plt.show()

    print("Сохранён:", graph2_path)


if __name__ == "__main__":
    plot_all()
