import ast
import html
import math
import operator

import streamlit as st


OPERATIONS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
INPUT_TRANSLATION = str.maketrans({"×": "*", "÷": "/", "−": "-"})
ALLOWED_INPUT_CHARACTERS = frozenset("0123456789.+-*/() ")


def evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATIONS:
        return OPERATIONS[type(node.op)](evaluate(node.left), evaluate(node.right))
    raise ValueError("Use numbers and +, -, *, or /.")


def calculate(expression: str) -> float:
    if len(expression) > 256:
        raise ValueError("Please keep the calculation under 256 characters.")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("That calculation is too long.")
    result = evaluate(tree)
    if not math.isfinite(result):
        raise ValueError("The answer is outside the supported range.")
    return result


def sanitize_input() -> None:
    expression = st.session_state.calculator_input.translate(INPUT_TRANSLATION)
    st.session_state.calculator_input = "".join(
        character
        for character in expression
        if character in ALLOWED_INPUT_CHARACTERS
    )
    st.session_state.calculator_error = ""


def press_button(label: str) -> None:
    expression = st.session_state.calculator_input

    if label == "AC":
        st.session_state.calculator_input = ""
        st.session_state.calculator_error = ""
    elif label == "DEL":
        st.session_state.calculator_input = expression[:-1]
        st.session_state.calculator_error = ""
    elif label == "=":
        try:
            result = calculate(expression)
            st.session_state.calculator_input = f"{result:.12g}"
            st.session_state.calculator_error = ""
        except (
            SyntaxError,
            ValueError,
            ZeroDivisionError,
            OverflowError,
            RecursionError,
        ) as error:
            st.session_state.calculator_error = str(error)
    else:
        st.session_state.calculator_input = expression + label
        st.session_state.calculator_error = ""


def main() -> None:
    st.set_page_config(page_title="Simple Calculator", page_icon="🧮", layout="centered")
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(ellipse at top, #26345a 0, #111827 55%, #0b1020 100%);
            color: #f8fafc;
        }
        .block-container { max-width: 520px; padding-top: 3rem; }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(22, 31, 51, .96);
            border: 1px solid #34415e;
            border-radius: 24px;
            box-shadow: 0 22px 60px rgba(0, 0, 0, .35);
            padding: 1.5rem;
        }
        .title { color: #fff; font-size: 2rem; font-weight: 800; text-align: center; }
        .live-result {
            color: #9eacc5;
            font-family: monospace;
            font-size: .9rem;
            line-height: 1.4rem;
            min-height: 1.4rem;
            overflow: hidden;
            text-align: right;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        div[data-testid="stTextInput"] input {
            background: #0d1424;
            border: 1px solid #3b4a6b;
            border-radius: 14px;
            color: #fff;
            font-family: monospace;
            font-size: clamp(1rem, 5vw, 1.7rem);
            min-height: 3.7rem;
            text-align: right;
        }
        div[data-testid="stTextInput"] div[data-testid="InputInstructions"] {
            display: none;
        }
        div.stButton > button {
            background: #26334d;
            border: 1px solid #394969;
            border-radius: 13px;
            color: #f8fafc;
            font-size: 1.15rem;
            font-weight: 700;
            min-height: 3.3rem;
        }
        div.stButton > button:hover { background: #394a6b; border-color: #7388b6; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "calculator_input" not in st.session_state:
        st.session_state.calculator_input = ""
        st.session_state.calculator_error = ""

    with st.container(border=True):
        st.markdown('<div class="title">Simple Calculator</div>', unsafe_allow_html=True)
        display = st.session_state.calculator_input
        preview = ""
        if display:
            try:
                preview = f"= {calculate(display):.12g}"
            except (
                SyntaxError,
                ValueError,
                ZeroDivisionError,
                OverflowError,
                RecursionError,
            ):
                pass
        st.markdown(
            f'<div class="live-result">{html.escape(preview)}</div>',
            unsafe_allow_html=True,
        )

        st.text_input(
            "Calculator display",
            key="calculator_input",
            placeholder="0",
            label_visibility="collapsed",
            on_change=sanitize_input,
        )

        rows = [
            ["AC", "DEL", "÷", "×"],
            ["7", "8", "9", "−"],
            ["4", "5", "6", "+"],
            ["1", "2", "3", "="],
            ["0", ".", "", ""],
        ]
        button_values = {"÷": "/", "×": "*", "−": "-"}

        for row_index, row in enumerate(rows):
            columns = st.columns(4, gap="small")
            for column, label in zip(columns, row):
                with column:
                    if label:
                        st.button(
                            label,
                            key=f"button-{row_index}-{label}",
                            use_container_width=True,
                            type="primary" if label == "=" else "secondary",
                            on_click=press_button,
                            args=(button_values.get(label, label),),
                        )

        if st.session_state.calculator_error:
            st.error(st.session_state.calculator_error)


if __name__ == "__main__":
    main()
