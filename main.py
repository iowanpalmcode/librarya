import json
import os
import random
import streamlit as st

from base_resources import base_resources
from trivia_questions import questions


# Persist library state (bookshelf + tags) to disk so it survives restarts.
STATE_PATH = os.path.join(os.path.dirname(__file__), "library_state.json")

def _load_library_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_library_state():
    state = {
        "bookshelf": st.session_state.get("bookshelf", []),
        "resource_tags": st.session_state.get("resource_tags", {}),
    }
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

# Ensure each major/category has at least 7 resources by adding filler links.
# This keeps the library feeling full even when we have lots of categories.
def _augment_resources(base):
    from collections import Counter

    res = list(base)
    counts = Counter(r["category"] for r in res)

    for cat, count in counts.items():
        for i in range(count, 7):
            res.append({
                "title": f"{cat} Resource {i + 1}",
                "url": f"https://duckduckgo.com/?q={cat.replace(' ', '+')}+learning+resources",
                "category": cat,
                "description": f"Additional {cat} learning resources."
            })

    return res

resources = _augment_resources(base_resources)

# Load saved state (bookshelf + tags) from disk
_saved = _load_library_state()

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'welcome'
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = 'All'
if 'bookshelf' not in st.session_state:
    st.session_state.bookshelf = _saved.get('bookshelf', [])
if 'resource_tags' not in st.session_state:
    st.session_state.resource_tags = _saved.get('resource_tags', {})
if 'fishing_stats' not in st.session_state:
    st.session_state.fishing_stats = {
        "casts": 0,
        "total_weight": 0,
        "best_catches": [],
        "achievements": [],
        "achievement_log": [],
        "notifications": [],
        "skill_tree": {
            "unspent_points": 0,
            "Luck": 0,
            "Strength": 0,
            "Technique": 0,
            "Patience": 0,
        },
    }

# Sidebar navigation
st.sidebar.title("Navigation")
pages = ["Welcome", "Library", "Bookshelf", "Relax", "Leaderboard", "Coffee", "Trivia"]
current_page = st.session_state.page.capitalize() if st.session_state.page else "Welcome"
if current_page not in pages:
    current_page = "Welcome"
page = st.sidebar.radio("Go to", pages, index=pages.index(current_page))
st.session_state.page = page.lower()

if st.session_state.page == 'welcome':
    st.title("📚 Welcome to the Digital Learning Library")
    st.markdown("""
    Hello! I'm your wonderful Librarian. I'm here to help you find the perfect learning resources.

    What category of books are you interested in today? Select a major or topic below, and I'll guide you to the library section.
    """)
    
    categories = sorted(list(set(res['category'] for res in resources)))
    selected = st.selectbox("Choose a category:", ["All"] + categories)
    
    if st.button("Enter the Library"):
        st.session_state.selected_category = selected
        st.session_state.page = 'library'
        st.rerun()
    st.markdown("Made in a day by Felix O.. check out some of my other projects @iowanpalmcode <--- Github btw")
elif st.session_state.page == 'library':
    st.title("📚 Digital Learning Library")

    st.markdown("Discover curated learning resources presented as books. Click on a book to visit the resource.")

    # Search functionality
    search_query = st.text_input("Search for resources by title or category:", key="library_search")

    # Category filter (additional)
    categories = sorted(list(set(res['category'] for res in resources)))
    current_category = st.session_state.get('selected_category', 'All')
    if current_category not in categories and current_category != 'All':
        current_category = 'All'
    category_index = 0 if current_category == 'All' else categories.index(current_category) + 1

    selected_category = st.selectbox(
        "Filter by category:",
        ["All"] + categories,
        index=category_index,
        key="library_category_filter"
    )

    # Filter resources based on selected category, then search, then tags (if any)
    filtered_resources = resources
    if selected_category != "All":
        filtered_resources = [res for res in filtered_resources if res['category'] == selected_category]

    if search_query:
        filtered_resources = [
            res for res in filtered_resources
            if search_query.lower() in res['title'].lower() or search_query.lower() in res['category'].lower()
        ]

    # Tag filter
    all_tags = sorted({t for tags in st.session_state.resource_tags.values() for t in tags})
    tag_filter = st.multiselect("Filter by tags:", all_tags, key="library_tag_filter")
    if tag_filter:
        filtered_resources = [
            res for res in filtered_resources
            if set(tag_filter).issubset(set(st.session_state.resource_tags.get(f"{res['category']}|{res['title']}", [])))
        ]

    # Display resources as "books"
    cols = st.columns(3)
    for i, res in enumerate(filtered_resources):
        with cols[i % 3]:
            with st.container():
                st.markdown(f"### 📖 {res['title']}")
                st.write(f"**Category:** {res['category']}")
                st.write(res['description'])

                res_id = f"{res['category']}|{res['title']}"

                # Favorites / bookshelf
                is_fav = any(b['id'] == res_id for b in st.session_state.bookshelf)
                if is_fav:
                    if st.button("⭐ Remove from Bookshelf", key=f"rm_{res_id}"):
                        st.session_state.bookshelf = [b for b in st.session_state.bookshelf if b['id'] != res_id]
                        save_library_state()
                        st.rerun()
                else:
                    if st.button("⭐ Add to Bookshelf", key=f"add_{res_id}"):
                        st.session_state.bookshelf.append({
                            "id": res_id,
                            "title": res['title'],
                            "url": res['url'],
                            "category": res['category'],
                            "description": res['description']
                        })
                        save_library_state()
                        st.rerun()

                # Tagging
                current_tags = st.session_state.resource_tags.get(res_id, [])
                if current_tags:
                    st.write("**Tags:**", ", ".join(current_tags))

                new_tag = st.text_input("Add tag", key=f"tag_{res_id}")
                if new_tag:
                    if st.button("Add Tag", key=f"add_tag_{res_id}"):
                        tags = set(st.session_state.resource_tags.get(res_id, []))
                        tags.add(new_tag.strip())
                        st.session_state.resource_tags[res_id] = sorted(tags)
                        save_library_state()
                        st.rerun()

                st.link_button("Read More", res['url'], use_container_width=True)
                st.divider()

    st.markdown("---")
    st.write("This library is powered by AI to curate the best learning resources. Enjoy!")

elif st.session_state.page == 'relax':
    st.title("🎣 Relax & Fish")
    st.markdown("Take a break and cast a line. Every catch is a surprise! Your skill and gear improve the more you fish.")

    st.markdown("""<style> form[data-testid="stForm"] button[type="submit"] { background-color: red !important; color: white !important; } </style>""", unsafe_allow_html=True)

    stats = st.session_state.fishing_stats
    casts = stats.get("casts", 0)
    total_weight = stats.get("total_weight", 0)
    best_catches = stats.get("best_catches", [])
    achievements = set(stats.get("achievements", []))
    achievement_log = stats.get("achievement_log", [])
    notifications = stats.get("notifications", [])
    skill_tree = stats.get("skill_tree", {
        "unspent_points": 0,
        "Luck": 0,
        "Strength": 0,
        "Technique": 0,
        "Patience": 0,
    })

    # Skill category values
    luck = skill_tree.get("Luck", 0)
    strength = skill_tree.get("Strength", 0)
    technique = skill_tree.get("Technique", 0)
    patience = skill_tree.get("Patience", 0)

    # Skill level increases with casts (better fish luck), with patience reducing the effective cast count
    effective_casts = casts + (patience // 2)

    # Level growth uses a linearly increasing cast requirement per level:
    #  Level 1 requires 5 casts, Level 2 requires 10 more, Level 3 requires 15 more, etc.
    base_req = 5
    inc_req = 5

    def total_casts_for_level(n: int) -> int:
        # total = base_req*n + inc_req * (n*(n-1)/2)
        return base_req * n + inc_req * (n * (n - 1) // 2)

    level = 0
    while total_casts_for_level(level + 1) <= effective_casts:
        level += 1

    casts_for_next = total_casts_for_level(level + 1) - effective_casts
    # Ensure level is at least 1 for display
    level = max(1, level)

    # Sidebar: recent achievement + stacked notifications
    last_ach = st.session_state.get("last_achievement")
    last_ach_desc = st.session_state.get("last_achievement_desc")
    with st.sidebar.expander("Recent Achievement", expanded=False):
        if last_ach:
            st.write(f"**{last_ach}**")
            if last_ach_desc:
                st.write(last_ach_desc)
        else:
            st.write("No achievements yet.")

    with st.sidebar.expander("Notifications", expanded=False):
        if notifications:
            for note in notifications:
                st.write(f"[{note['time']}] {note['message']}")
        else:
            st.write("No notifications yet.")

    achievement_descriptions = {
        "First Cast": "You made your first cast—now the real fishing begins!",
        "Tenacious Angler": "You've cast 10 times. Keep going; greatness is waiting in the deep!",
        "Fishing Veteran": "50 casts down. Your reflexes and patience are improving.",
        "Heavy Hitter": "You've pulled in a total of 100+ lbs of fish. That's a hefty haul!",
        "Beast Mode": "A single catch over 20 lbs! You’re getting strong.",
        "Big Game Fishing": "You landed a big-game fish. Trophy season!",
        "Legendary Catch": "You caught the Legendary Leviathan. Mythic status achieved.",
        "Skill Master": "Your skill tree is impressive—your techniques are refined.",
    }

    def log_notification(message: str):
        timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        notifications.insert(0, {"time": timestamp, "message": message})
        # Keep last 10 notifications
        if len(notifications) > 10:
            notifications.pop()

    def unlock_achievement(name: str):
        if name not in achievements:
            achievements.add(name)
            desc = achievement_descriptions.get(name, "")
            now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            achievement_log.insert(0, {"time": now, "name": name, "desc": desc})
            log_notification(f"🏅 {name}: {desc}")
            st.session_state.last_achievement = name
            st.session_state.last_achievement_desc = desc

    # Skill branch perks (additional effects unlocked as you invest points)
    skill_perks = {
        "Luck": [
            (1, "Slightly increased chance to catch rare fish."),
            (3, "Occasionally triggers a Lucky Strike (+25% weight)."),
            (6, "Small chance to receive an extra skill point on cast."),
            (10, "Greatly increased chance for legendary catches."),
        ],
        "Strength": [
            (1, "Increases minimum catch weight."),
            (3, "Adds bonus weight to every catch."),
            (6, "Small chance to double your catch weight."),
            (10, "Strongest catches become much heavier."),
        ],
        "Technique": [
            (1, "Improves consistency of catches."),
            (3, "Catches will trend toward the higher end of the range."),
            (6, "Catches become much more consistent and predictable."),
            (10, "Masterful technique grants near-perfect catches."),
        ],
        "Patience": [
            (1, "Occasionally grants an extra skill point."),
            (3, "Increases chance to earn bonus skill points."),
            (6, "Makes level-ups feel quicker."),
            (10, "You gain a steady stream of bonus points as you wait."),
        ],
    }

    def unlock_achievement(name: str):
        if name not in achievements:
            achievements.add(name)
            desc = achievement_descriptions.get(name, "")
            now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            achievement_log.insert(0, {"time": now, "name": name, "desc": desc})
            log_notification(f"🏅 {name}: {desc}")
            st.session_state.last_achievement = name
            st.session_state.last_achievement_desc = desc

    # Achievement checks (called each cast)
    def check_achievements(latest_catch: str, latest_weight: int):
        if casts >= 1:
            unlock_achievement("First Cast")
        if casts >= 10:
            unlock_achievement("Tenacious Angler")
        if casts >= 50:
            unlock_achievement("Fishing Veteran")
        if total_weight >= 100:
            unlock_achievement("Heavy Hitter")
        if latest_weight >= 20:
            unlock_achievement("Beast Mode")
        if latest_catch in ["Marlin", "Shark", "Swordfish"]:
            unlock_achievement("Big Game Fishing")
        if latest_catch == "Legendary Leviathan":
            unlock_achievement("Legendary Catch")
        if sum(skill_tree.values()) >= 20:
            unlock_achievement("Skill Master")

    # Fish pool (with rarities)
    fish_pool = [
        {"name": "Minnow", "min": 1, "max": 3, "rarity": "Common"},
        {"name": "Perch", "min": 2, "max": 5, "rarity": "Common"},
        {"name": "Trout", "min": 3, "max": 8, "rarity": "Common"},
        {"name": "Bass", "min": 4, "max": 10, "rarity": "Common"},
        {"name": "Carp", "min": 5, "max": 12, "rarity": "Uncommon"},
        {"name": "Salmon", "min": 6, "max": 15, "rarity": "Uncommon"},
        {"name": "Tuna", "min": 8, "max": 18, "rarity": "Uncommon"},
        {"name": "Pike", "min": 7, "max": 16, "rarity": "Uncommon"},
        {"name": "Walleye", "min": 5, "max": 14, "rarity": "Uncommon"},
        {"name": "Catfish", "min": 6, "max": 17, "rarity": "Rare"},
        {"name": "Steelhead", "min": 8, "max": 20, "rarity": "Rare"},
        {"name": "Swordfish", "min": 10, "max": 22, "rarity": "Rare"},
        {"name": "Shark", "min": 12, "max": 25, "rarity": "Rare"},
        {"name": "Marlin", "min": 15, "max": 30, "rarity": "Legendary"},
        {"name": "Legendary Leviathan", "min": 20, "max": 40, "rarity": "Mythic"},
        {"name": "Golden Trout", "min": 10, "max": 23, "rarity": "Legendary"},
        {"name": "Ancient Sturgeon", "min": 18, "max": 35, "rarity": "Legendary"},
        {"name": "Celestial Manta", "min": 22, "max": 45, "rarity": "Mythic"},
    ]

    rarity_base_weights = {
        "Common": 50,
        "Uncommon": 30,
        "Rare": 12,
        "Legendary": 5,
        "Mythic": 1,
    }

    if st.button("Cast Line"):
        # Earn skill points each cast; high-tier branches give multipliers
        max_branch_level = max(luck, strength, technique, patience)
        bonus_points = max(0, max_branch_level // 5)
        skill_tree["unspent_points"] = skill_tree.get("unspent_points", 0) + 1 + bonus_points
        if bonus_points > 0:
            log_notification(f"Skill gain boosted by +{bonus_points} (high-tier branch).")

        # Determine fish selection weights
        raw_weights = []
        for fish in fish_pool:
            rarity_weight = rarity_base_weights.get(fish["rarity"], 1)
            luck_factor = 1 + (luck * 0.07)
            level_factor = 1 + (level * 0.02)
            raw_weights.append(rarity_weight * luck_factor * level_factor)

        chosen = random.choices(fish_pool, weights=raw_weights, k=1)[0]
        catch = chosen["name"]

        # Apply strength and technique to weight range
        min_w = chosen["min"] + strength + (level // 3)
        max_w = chosen["max"] + strength + technique + (level // 2)

        # Technique improves consistency and biases toward the higher end
        if technique >= 3:
            min_w = int(min_w + (max_w - min_w) * 0.15)
        if technique >= 6:
            min_w = int(min_w + (max_w - min_w) * 0.20)

        # Base weight
        weight = random.randint(min_w, max_w)

        # Luck: chance for a lucky strike (bonus weight)
        if luck >= 2 and random.random() < min(0.10, luck * 0.02):
            bonus = int(weight * 0.25)
            weight += bonus
            st.info("🍀 Lucky strike! Your catch weighed more than expected.")

        # Patience: chance for an extra skill point
        if random.random() < min(0.15, 0.02 + patience * 0.03):
            skill_tree["unspent_points"] += 1
            st.info("Your patience paid off! You earned an extra skill point.")

        st.session_state.last_catch = (catch, weight)
        casts += 1
        total_weight += weight

        # Track leaderboard (top catches)
        best_catches.append((catch, weight))
        best_catches = sorted(best_catches, key=lambda x: x[1], reverse=True)[:10]

        check_achievements(catch, weight)

        stats.update({
            "casts": casts,
            "total_weight": total_weight,
            "best_catches": best_catches,
            "achievements": sorted(achievements),
            "achievement_log": achievement_log,
            "notifications": notifications,
            "skill_tree": skill_tree,
        })
        st.session_state.fishing_stats = stats
        save_library_state()

    # Display last catch
    if st.session_state.get("last_catch"):
        fish, weight = st.session_state.last_catch
        st.success(f"You caught a {weight} lb {fish}!")
        st.progress(min(weight / 45, 1.0))

    # Stats summary
    avg_weight = (total_weight / casts) if casts > 0 else 0
    st.markdown(
        f"**Casts:** {casts}  |  **Avg weight:** {avg_weight:.1f} lbs  |  **Skill level:** {level}"
    )
    st.write(f"**Casts to next level:** {casts_for_next}")

    # Skill tree UI
    with st.expander("🔧 Skill Tree & Points"):
        unspent = skill_tree.get("unspent_points", 0)
        st.write(f"Unspent skill points: **{unspent}**")

        if unspent > 0:
            points_to_invest = st.number_input(
                "Points to invest:",
                min_value=1,
                max_value=unspent,
                value=1,
                step=1,
                key="invest_points"
            )
        else:
            points_to_invest = 0

        cols = st.columns(4)
        for idx, branch in enumerate(["Luck", "Strength", "Technique", "Patience"]):
            with cols[idx]:
                level_val = skill_tree.get(branch, 0)
                st.write(f"**{branch}**: {level_val}")
                if unspent > 0:
                    if st.button(f"Invest in {branch}", key=f"invest_{branch}"):
                        invest_amount = min(points_to_invest, skill_tree.get("unspent_points", 0))
                        if invest_amount > 0:
                            skill_tree[branch] = skill_tree.get(branch, 0) + invest_amount
                            skill_tree["unspent_points"] -= invest_amount
                            log_notification(f"Invested {invest_amount} point(s) into {branch}.")
                            stats["skill_tree"] = skill_tree
                            st.session_state.fishing_stats = stats
                            save_library_state()
                            st.rerun()

                # Show tiered skill perks
                perks = skill_perks.get(branch, [])
                current_perk = None
                next_perk = None
                for lvl, desc in perks:
                    if level_val >= lvl:
                        current_perk = desc
                    elif next_perk is None:
                        next_perk = (lvl, desc)
                if current_perk:
                    st.caption(f"Perk: {current_perk}")
                if next_perk:
                    st.caption(f"Next ({next_perk[0]}): {next_perk[1]}")

    # Achievements (with log)
    with st.expander("🏆 Achievements"):
        if achievement_log:
            for entry in achievement_log[:20]:
                st.write(f"[{entry['time']}] **{entry['name']}** — {entry['desc']}")
        else:
            st.write("Cast a line to unlock achievements!")

    # Leaderboard callout
    if best_catches:
        top = best_catches[0]
        st.info(f"🎉 Best catch: {top[1]} lb {top[0]}")

elif st.session_state.page == 'leaderboard':
    st.title("🏆 Fishing Leaderboard")
    st.markdown("Top 3 heaviest catches from your sessions.")

    stats = st.session_state.fishing_stats
    best_catches = stats.get("best_catches", [])

    if not best_catches:
        st.info("No catches yet. Head to Relax & Fish and cast a line!")
    else:
        for idx, (fish, weight) in enumerate(best_catches[:3], start=1):
            st.markdown(f"**#{idx} — {weight} lb {fish}**")

    st.markdown("---")
    total_casts = stats.get("casts", 0)
    total_weight = stats.get("total_weight", 0)
    avg_weight = (total_weight / total_casts) if total_casts else 0
    st.write(f"**Total casts:** {total_casts}")
    st.write(f"**Total weight:** {total_weight} lbs")
    st.write(f"**Average weight:** {avg_weight:.1f} lbs")

elif st.session_state.page == 'coffee':
    st.title("☕ Coffee Lounge")
    st.markdown("Chat with a virtual barista and brew a fresh cup while you browse learning resources.")

    if 'coffee_choice' not in st.session_state:
        st.session_state.coffee_choice = None
        st.session_state.coffee_tip = None

    if st.button("Brew a Cup"):
        coffees = ["Espresso", "Latte", "Cappuccino", "Americano", "Pour Over", "French Press", "Cold Brew"]
        tips = [
            "Try using freshly ground beans for best flavor.",
            "A 1:16 coffee-to-water ratio is a great starting point.",
            "Let it bloom for 30 seconds before pouring.",
            "Use filtered water for a cleaner cup.",
            "Keep your equipment clean to avoid stale flavors."
        ]
        st.session_state.coffee_choice = random.choice(coffees)
        st.session_state.coffee_tip = random.choice(tips)

    if st.session_state.coffee_choice:
        st.success(f"Here's your {st.session_state.coffee_choice}!")
        st.write(st.session_state.coffee_tip)

elif st.session_state.page == 'bookshelf':
    st.title("📚 My Bookshelf")
    st.markdown("Your saved learning resources appear here. Remove items when you're done.")

    if not st.session_state.bookshelf:
        st.info("Your bookshelf is empty. Add resources from the Library page.")
    else:
        cols = st.columns(2)
        for i, book in enumerate(st.session_state.bookshelf):
            with cols[i % 2]:
                st.markdown(f"### 📖 {book['title']}")
                st.write(f"**Category:** {book['category']}")
                st.write(book['description'])
                if st.button("Remove", key=f"remove_{book['id']}"):
                    st.session_state.bookshelf = [b for b in st.session_state.bookshelf if b['id'] != book['id']]
                    save_library_state()
                    st.rerun()
                st.link_button("Open Link", book['url'], use_container_width=True)

        if st.button("Clear Bookshelf"):
            st.session_state.bookshelf = []
            save_library_state()
            st.rerun()

elif st.session_state.page == 'trivia':
    st.title("🧠 Learning Trivia")
    st.markdown("Test your knowledge with quick questions about learning resources and majors.")

    # Initialize shuffled questions
    if 'shuffled_questions' not in st.session_state or not st.session_state.shuffled_questions:
        st.session_state.shuffled_questions = questions.copy()
        random.shuffle(st.session_state.shuffled_questions)

    # Initialize statistics
    if 'trivia_total_answered' not in st.session_state:
        st.session_state.trivia_total_answered = 0
    if 'trivia_correct' not in st.session_state:
        st.session_state.trivia_correct = 0
    if 'trivia_wrong' not in st.session_state:
        st.session_state.trivia_wrong = 0

    # Calculate percentage
    if st.session_state.trivia_total_answered > 0:
        percentage = (st.session_state.trivia_correct / st.session_state.trivia_total_answered) * 100
    else:
        percentage = 0

    st.markdown(f"**Statistics:** Total Answered: {st.session_state.trivia_total_answered}, Correct: {st.session_state.trivia_correct}, Wrong: {st.session_state.trivia_wrong}, % Right: {percentage:.1f}%")

    if 'trivia_question' not in st.session_state:
        st.session_state.trivia_question = None
        st.session_state.trivia_answer = None
        st.session_state.trivia_result = None

    if st.button("New Question") or st.session_state.trivia_question is None:
        if st.session_state.shuffled_questions:
            st.session_state.trivia_question = st.session_state.shuffled_questions.pop(0)
        else:
            # Reshuffle when all questions are done
            st.session_state.shuffled_questions = questions.copy()
            random.shuffle(st.session_state.shuffled_questions)
            st.session_state.trivia_question = st.session_state.shuffled_questions.pop(0)
        st.session_state.trivia_answer = None
        st.session_state.trivia_result = None

    if st.session_state.trivia_question:
        st.write(st.session_state.trivia_question["q"])
        st.session_state.trivia_answer = st.radio(
            "Choose an answer:",
            st.session_state.trivia_question["options"],
            key="trivia_choice"
        )

        if st.button("Submit Answer"):
            correct = st.session_state.trivia_question["a"]
            st.session_state.trivia_total_answered += 1
            if st.session_state.trivia_answer == correct:
                st.session_state.trivia_correct += 1
                st.success("Correct! Great job.")
            else:
                st.session_state.trivia_wrong += 1
                st.error(f"Not quite — the correct answer was: {correct}.")
