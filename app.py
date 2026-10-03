import ast
import html
import math
import operator
import re

import streamlit as st


OPERATIONS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
SCIENTIFIC_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "ln": math.log,
    "log": math.log10,
}
SCIENTIFIC_CONSTANTS = {"pi": math.pi, "e": math.e}
SCIENTIFIC_NAMES = frozenset(SCIENTIFIC_FUNCTIONS) | frozenset(SCIENTIFIC_CONSTANTS)
INPUT_TRANSLATION = str.maketrans(
    {"×": "*", "÷": "/", "−": "-", "π": "pi", "√": "sqrt"}
)
ALLOWED_INPUT_CHARACTERS = (
    frozenset("0123456789.+-*/() ") | frozenset("".join(SCIENTIFIC_NAMES))
)
LIVE_PREVIEW_SCRIPT = """
<script>
(() => {
  if (window.__calculatorLivePreviewInstalled) return;
  window.__calculatorLivePreviewInstalled = true;

  const names = ["sin", "cos", "tan", "sqrt", "ln", "log", "pi", "e"];
  const functions = {
    sin: Math.sin,
    cos: Math.cos,
    tan: Math.tan,
    sqrt: Math.sqrt,
    ln: Math.log,
    log: Math.log10
  };

  function normalize(value) {
    return value
      .replaceAll("×", "*")
      .replaceAll("÷", "/")
      .replaceAll("−", "-")
      .replaceAll("π", "pi")
      .replaceAll("√", "sqrt");
  }

  function sanitize(value) {
    const allowed = value.replace(/[^0-9.+\\-*/() \\tA-Za-z]/g, "");
    return allowed.replace(/[A-Za-z]+/g, word =>
      names.includes(word) || names.some(name => name.startsWith(word))
        ? word
        : ""
    );
  }

  function evaluate(source) {
    if (!source.trim() || source.length > 256) throw new Error("incomplete");
    const tokens = source.match(/\\d+(?:\\.\\d*)?|\\.\\d+|[A-Za-z]+|\\*\\*|[()+\\-*/]/g) || [];
    if (tokens.join("") !== source.replace(/\\s/g, "") || tokens.length > 100) {
      throw new Error("invalid");
    }
    let index = 0;

    function expression() {
      let value = term();
      while (tokens[index] === "+" || tokens[index] === "-") {
        const operation = tokens[index++];
        const right = term();
        value = operation === "+" ? value + right : value - right;
      }
      return value;
    }

    function term() {
      let value = unary();
      while (tokens[index] === "*" || tokens[index] === "/") {
        const operation = tokens[index++];
        const right = unary();
        value = operation === "*" ? value * right : value / right;
        if (!Number.isFinite(value)) throw new Error("invalid");
      }
      return value;
    }

    function unary() {
      if (tokens[index] === "+") {
        index++;
        return unary();
      }
      if (tokens[index] === "-") {
        index++;
        return -unary();
      }
      return power();
    }

    function power() {
      let value = primary();
      if (tokens[index] === "**") {
        index++;
        value **= unary();
      }
      if (!Number.isFinite(value)) throw new Error("invalid");
      return value;
    }

    function primary() {
      const token = tokens[index++];
      if (token === "(") {
        const value = expression();
        if (tokens[index++] !== ")") throw new Error("incomplete");
        return value;
      }
      if (token === "pi") return Math.PI;
      if (token === "e") return Math.E;
      if (Object.hasOwn(functions, token)) {
        if (tokens[index++] !== "(") throw new Error("incomplete");
        const argument = expression();
        if (tokens[index++] !== ")") throw new Error("incomplete");
        return functions[token](argument);
      }
      if (token && /^\\d+(?:\\.\\d*)?$|^\\.\\d+$/.test(token)) {
        return Number(token);
      }
      throw new Error("incomplete");
    }

    const result = expression();
    if (index !== tokens.length || !Number.isFinite(result)) {
      throw new Error("incomplete");
    }
    return result;
  }

  document.addEventListener("input", event => {
    const input = event.target;
    if (!(input instanceof HTMLInputElement) ||
        !input.closest('[data-testid="stTextInput"]')) return;

    const cleaned = sanitize(normalize(input.value));
    if (cleaned !== input.value) input.value = cleaned;

    const preview = document.querySelector(".live-result");
    if (!preview) return;
    try {
      preview.textContent = `= ${Number(evaluate(cleaned).toPrecision(12))}`;
    } catch {
      preview.textContent = "";
    }
  }, true);
})();
</script>
"""


def evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in SCIENTIFIC_CONSTANTS:
        return SCIENTIFIC_CONSTANTS[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATIONS:
        left = evaluate(node.left)
        right = evaluate(node.right)
        if isinstance(node.op, ast.Pow) and left < 0 and not right.is_integer():
            raise ValueError("A negative number cannot have a fractional power.")
        result = OPERATIONS[type(node.op)](left, right)
        if not isinstance(result, (int, float)) or not math.isfinite(result):
            raise ValueError("The answer is outside the supported range.")
        return float(result)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in SCIENTIFIC_FUNCTIONS
        and len(node.args) == 1
        and not node.keywords
    ):
        return SCIENTIFIC_FUNCTIONS[node.func.id](evaluate(node.args[0]))
    raise ValueError(
        "Use numbers, +, -, *, /, powers, parentheses, sin, cos, tan, "
        "sqrt, ln, log, pi, or e."
    )


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
    expression = re.sub(
        r"[A-Za-z]+",
        lambda match: match.group(0) if match.group(0) in SCIENTIFIC_NAMES else "",
        expression,
    )
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
    st.set_page_config(
        page_title="Scientific Calculator", page_icon="🧮", layout="centered"
    )
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
            transition: background-color .12s ease, border-color .12s ease,
                box-shadow .12s ease, transform .12s ease;
        }
        div.stButton > button:hover {
            background: #394a6b;
            border-color: #7388b6;
        }
        div.stButton > button:active {
            background: #52678f;
            border-color: #a8bbdf;
            box-shadow: inset 0 3px 7px rgba(0, 0, 0, .35);
            transform: translateY(2px) scale(.98);
        }
        div.stButton > button:focus {
            border-color: #a8bbdf;
            box-shadow: 0 0 0 3px rgba(116, 152, 218, .4);
            outline: none;
        }
        .st-key-button-3-AC div.stButton > button {
            background: #8f3544;
            border-color: #bd5262;
        }
        .st-key-button-3-AC div.stButton > button:hover,
        .st-key-button-3-AC div.stButton > button:focus {
            background: #b54152;
            border-color: #ed8290;
        }
        .st-key-button-3-DEL div.stButton > button {
            background: #805221;
            border-color: #b67c36;
        }
        .st-key-button-3-DEL div.stButton > button:hover,
        .st-key-button-3-DEL div.stButton > button:focus {
            background: #a86b28;
            border-color: #e1a858;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "calculator_input" not in st.session_state:
        st.session_state.calculator_input = ""
        st.session_state.calculator_error = ""

    with st.container(border=True):
        st.markdown(
            '<div class="title">Scientific Calculator</div>', unsafe_allow_html=True
        )
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
        st.html(LIVE_PREVIEW_SCRIPT, unsafe_allow_javascript=True)

        rows = [
            ["sin", "cos", "tan", "√"],
            ["ln", "log", "π", "e"],
            ["x²", "(", ")", ""],
            ["AC", "DEL", "÷", "×"],
            ["7", "8", "9", "−"],
            ["4", "5", "6", "+"],
            ["1", "2", "3", "="],
            ["0", ".", "", ""],
        ]
        button_values = {
            "sin": "sin(",
            "cos": "cos(",
            "tan": "tan(",
            "√": "sqrt(",
            "ln": "ln(",
            "log": "log(",
            "π": "pi",
            "x²": "**2",
            "÷": "/",
            "×": "*",
            "−": "-",
        }

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
