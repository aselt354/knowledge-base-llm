import matplotlib.pyplot as plt
import matplotlib
import json
import numpy as np

matplotlib.rcParams['font.family'] = 'DejaVu Sans'

def plot_all(json_path="results_20260519_041147.json"):
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
    for key in ["всегда наблюдается", "может наблюдаться", "всегда отсутствует", "может отсутствовать"]:
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
                   label='Шаг 1: тип связи', color='#2E75B6', alpha=0.9)
    bars2 = ax.bar(x + width/2, step2_vals, width,
                   label='Шаг 2: уточнение', color='#ED7D31', alpha=0.9)

    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2., h + 1.5,
                   f'{h:.0f}%', ha='center', va='bottom',
                   fontsize=10, fontweight='bold', color='#2E75B6')

    for bar in bars2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2., h + 1.5,
                   f'{h:.0f}%', ha='center', va='bottom',
                   fontsize=10, fontweight='bold', color='#ED7D31')

    ax.set_title(
        "Точность системы по категориям связей\n"
        "(предметная область: клиническая диагностика)",
        fontsize=12, fontweight='bold'
    )
    ax.set_ylabel("Точность (%)", fontsize=11)
    ax.set_xlabel("Категория связи", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(cat_names, fontsize=10)
    ax.set_ylim(0, 120)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3, linewidth=1)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig("graph1_by_category.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("Сохранён: graph1_by_category.png")

    # --------------------------------------------------------
    # ГРАФИК 2 — общая точность прямое vs обратное
    # --------------------------------------------------------
    directions = ['Прямое\nнаправление', 'Обратное\nнаправление']
    step1_dir = [totals["step1_acc"], totals.get("rev_step1_acc", 100.0)]
    step2_dir = [totals["step2_acc"], totals.get("rev_step2_acc", 66.7)]

    x2 = np.arange(len(directions))

    fig2, ax2 = plt.subplots(figsize=(8, 6))

    bars3 = ax2.bar(x2 - width/2, step1_dir, width,
                    label='Шаг 1: тип связи', color='#2E75B6', alpha=0.9)
    bars4 = ax2.bar(x2 + width/2, step2_dir, width,
                    label='Шаг 2: уточнение', color='#ED7D31', alpha=0.9)

    for bar in bars3:
        h = bar.get_height()
        if h > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., h + 1.5,
                    f'{h:.1f}%', ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color='#2E75B6')

    for bar in bars4:
        h = bar.get_height()
        if h > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., h + 1.5,
                    f'{h:.1f}%', ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color='#ED7D31')

    ax2.set_title(
        "Общая точность по направлениям связи\n"
        "(предметная область: клиническая диагностика)",
        fontsize=12, fontweight='bold'
    )
    ax2.set_ylabel("Точность (%)", fontsize=11)
    ax2.set_xlabel("Направление", fontsize=11)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(directions, fontsize=11)
    ax2.set_ylim(0, 120)
    ax2.axhline(y=100, color='gray', linestyle='--', alpha=0.3, linewidth=1)
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig("graph2_directions.png", dpi=150, bbox_inches='tight')
    plt.show()
    print("Сохранён: graph2_directions.png")


if __name__ == "__main__":
    plot_all("results_20260519_041147.json")
    print("\nГотово! Сохранены:")
    print("  graph1_by_category.png")
    print("  graph2_directions.png")