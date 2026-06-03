# Run with: streamlit run app.py

import random
import streamlit as st
from algorithm import (
    load_vocab, load_scores, save_scores, update_score,
    get_weighted_words, get_boss_words, get_stats_table,
)

VOCAB_FILE    = "vocab.csv"
QUIZ_LENGTH   = 10
BOSS_HP       = 10
PLAYER_HP     = 5
CHOICES_COUNT = 4

st.set_page_config(page_title="IB Mandarin Vocab Quiz", layout="centered",
                   initial_sidebar_state="collapsed")

#Styling

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Serif', serif !important;
}
div.stButton > button {
    border-radius: 14px;
    font-family: 'Noto Serif', serif;
    font-weight: 600;
    letter-spacing: 0.02em;
}
div.stButton > button:hover {
    background-color: inherit !important;
    color: inherit !important;
    border-color: inherit !important;
    opacity: 1 !important;
}
h1 { color: #8B1A1A !important; letter-spacing: 0.05em; }
h2, h3 { color: #5C3317 !important; }
.mq-card {
    background: #EEE8DF;
    border: 1px solid #C8BAA8;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.mq-hanzi {
    font-size: 4rem;
    text-align: center;
    color: #8B1A1A;
    line-height: 1.2;
}
.mq-pinyin {
    text-align: center;
    color: #8A7560;
    font-style: italic;
    margin-bottom: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

#Data

@st.cache_data
def get_vocab():
    return load_vocab(VOCAB_FILE)

def get_scores():
    return load_scores()

#Session state

def init_state():
    defaults = {
        "nav_tab": "Quiz",
        "mode": None, "quiz_words": [], "quiz_index": 0,
        "player_hp": PLAYER_HP, "boss_hp": BOSS_HP, "coins": 0,
        "feedback": None, "choices": [], "answered": False,
        "session_correct": 0, "session_total": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_session(mode, words):
    st.session_state.update({
        "mode": mode, "quiz_words": words, "quiz_index": 0,
        "player_hp": PLAYER_HP, "boss_hp": BOSS_HP, "coins": 0,
        "feedback": None, "choices": [], "answered": False,
        "session_correct": 0, "session_total": 0,
    })

def end_session():
    st.session_state.mode = None
    st.cache_data.clear()

def make_choices(correct, all_vocab):
    pool = [w for w in all_vocab if w["hanzi"] != correct["hanzi"]]
    opts = random.sample(pool, k=min(CHOICES_COUNT - 1, len(pool))) + [correct]
    random.shuffle(opts)
    return opts

#Shared UI

def question_card(word):
    st.markdown(
        f"<div class='mq-card'>"
        f"<div class='mq-hanzi'>{word['hanzi']}</div>"
        f"<div class='mq-pinyin'>{word['pinyin']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("**What does this mean?**")

def answer_buttons(word, vocab, prefix):
    if not st.session_state.choices:
        st.session_state.choices = make_choices(word, vocab)
    chosen = None
    left, right = st.columns(2)
    for i, choice in enumerate(st.session_state.choices):
        col = left if i % 2 == 0 else right
        if st.session_state.answered:
            if choice["hanzi"] == word["hanzi"]:
                col.success(f"✓  {choice['english']}")
            else:
                col.button(choice["english"], disabled=True,
                           use_container_width=True, key=f"{prefix}_d{i}")
        else:
            if col.button(choice["english"], use_container_width=True,
                          key=f"{prefix}_b{i}"):
                chosen = choice["hanzi"]
    return chosen

def hp_display(player_hp, boss_hp=None):
    hearts = "❤️" * player_hp + "🖤" * (PLAYER_HP - player_hp)
    if boss_hp is not None:
        boss = "●" * boss_hp + "○" * (BOSS_HP - boss_hp)
        c1, c2 = st.columns(2)
        c1.markdown(f"**You:** {hearts}")
        c2.markdown(f"**Boss:** {boss}")
    else:
        st.markdown(f"**HP:** {hearts}")

#Quiz tab

def tab_quiz(vocab, scores):
    if st.session_state.mode != "quiz":
        st.subheader("Adaptive quiz")
        attempted = sum(1 for v in scores.values() if v.get("attempts", 0) > 0)
        avg = (sum(v["correct"] / v["attempts"] for v in scores.values()
                   if v.get("attempts", 0) > 0) / attempted
               if attempted else None)
        c1, c2, c3 = st.columns(3)
        c1.metric("Words in deck", len(vocab))
        c2.metric("Practiced", attempted)
        c3.metric("Avg accuracy", f"{round(avg*100,1)}%" if avg else "—")
        st.write("")
        if st.button("Start quiz", use_container_width=True):
            reset_session("quiz", get_weighted_words(vocab, scores, QUIZ_LENGTH))
            st.rerun()
        return

    words = st.session_state.quiz_words
    idx   = st.session_state.quiz_index

    if idx >= len(words):
        c = st.session_state.session_correct
        t = st.session_state.session_total
        st.subheader("Session complete")
        st.metric("Score", f"{c} / {t}")
        if c == t:             st.success("Perfect!")
        elif c / max(t,1) >= 0.7: st.info("Good work.")
        else:                  st.warning("Keep drilling.")
        if st.button("Back"):
            end_session(); st.rerun()
        return

    word = words[idx]
    st.progress(idx / len(words), text=f"Question {idx+1} of {len(words)}")
    hp_display(st.session_state.player_hp)
    st.divider()
    question_card(word)
    chosen = answer_buttons(word, vocab, "q")

    if chosen and not st.session_state.answered:
        ok = chosen == word["hanzi"]
        save_scores(update_score(scores, word["hanzi"], ok))
        st.session_state.answered       = True
        st.session_state.session_total += 1
        st.session_state.feedback       = "correct" if ok else "wrong"
        if ok:
            st.session_state.coins           += 1
            st.session_state.session_correct += 1
        else:
            st.session_state.player_hp = max(0, st.session_state.player_hp - 1)
        st.rerun()

    if st.session_state.answered:
        if st.session_state.feedback == "correct":
            st.success("Correct!")
        else:
            st.error(f"Wrong --> answer was **{word['english']}**")

        if st.session_state.player_hp == 0:
            st.warning("Out of hearts.")
            if st.button("Back"): end_session(); st.rerun()
        elif st.button("Next"):
            st.session_state.quiz_index += 1
            st.session_state.feedback    = None
            st.session_state.answered    = False
            st.session_state.choices     = []
            st.rerun()

#Boss tab

def tab_boss(vocab, scores):
    if st.session_state.mode != "boss":
        st.subheader("Boss battle")
        st.markdown(
            "<div class='mq-card'>The boss is built from your weakest words. "
            "Each correct answer deals 1 damage. Each mistake costs 1 HP.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Fight boss", use_container_width=True):
            reset_session("boss", get_boss_words(vocab, scores, BOSS_HP))
            st.rerun()
        return

    if st.session_state.boss_hp <= 0:
        st.subheader("Boss defeated!")
        st.balloons()
        if st.button("Back"): end_session(); st.rerun()
        return

    if st.session_state.player_hp <= 0:
        st.subheader("Defeated")
        st.error("You lost.")
        c1, c2 = st.columns(2)
        if c1.button("Try again"):
            reset_session("boss", get_boss_words(vocab, scores, BOSS_HP)); st.rerun()
        if c2.button("Back"):
            end_session(); st.rerun()
        return

    words = st.session_state.quiz_words
    word  = words[st.session_state.quiz_index % len(words)]

    hp_display(st.session_state.player_hp, st.session_state.boss_hp)
    st.progress(st.session_state.boss_hp / BOSS_HP,
                text=f"Boss HP: {st.session_state.boss_hp} / {BOSS_HP}")
    st.divider()
    question_card(word)
    chosen = answer_buttons(word, vocab, "b")

    if chosen and not st.session_state.answered:
        ok = chosen == word["hanzi"]
        save_scores(update_score(scores, word["hanzi"], ok))
        st.session_state.answered = True
        st.session_state.feedback = "correct" if ok else "wrong"
        if ok:
            st.session_state.boss_hp = max(0, st.session_state.boss_hp - 1)
        else:
            st.session_state.player_hp = max(0, st.session_state.player_hp - 1)
        st.rerun()

    if st.session_state.answered:
        if st.session_state.feedback == "correct":
            st.success(f"Hit! Boss HP: {st.session_state.boss_hp}")
        else:
            st.error(f"Wrong --> answer was **{word['english']}**")
        if st.session_state.boss_hp > 0 and st.session_state.player_hp > 0:
            if st.button("Next"):
                st.session_state.quiz_index += 1
                st.session_state.feedback    = None
                st.session_state.answered    = False
                st.session_state.choices     = []
                st.rerun()

#Stats tab

def tab_stats(vocab, scores):
    st.subheader("Progress")
    df       = get_stats_table(vocab, scores)
    attempted = df[df["Attempts"] > 0]

    if attempted.empty:
        st.info("Complete a quiz session to see stats.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Practiced", len(attempted))
    c2.metric("Avg weakness", round(attempted["Weakness"].mean(), 3))
    c3.metric("Untouched", len(df) - len(attempted))

    st.divider()
    t1, t2 = st.tabs(["Needs work", "Full table"])
    with t1:
        weak = attempted[attempted["Weakness"] > 0.3].head(20)
        if weak.empty:
            st.success("No critical weak spots.")
        else:
            st.dataframe(weak[["Word","Pinyin","English","Correct %","Weakness"]],
                         use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(
            attempted[["Word","Pinyin","English","Attempts","Correct %","Weakness"]],
            use_container_width=True, hide_index=True)

#Main

def main():
    init_state()
    st.title("IB Mandarin Vocab Quiz")

    try:
        vocab = get_vocab()
    except FileNotFoundError:
        st.error(f"'{VOCAB_FILE}' not found. Place it in the same folder as app.py.")
        st.stop()

    scores = get_scores()
    st.radio(
        "", ["Quiz", "Boss Battle", "My Stats"],
        key="nav_tab",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    if   st.session_state.nav_tab == "Quiz":        tab_quiz(vocab, scores)
    elif st.session_state.nav_tab == "Boss Battle": tab_boss(vocab, scores)
    else:                                           tab_stats(vocab, scores)

if __name__ == "__main__":
    main()
