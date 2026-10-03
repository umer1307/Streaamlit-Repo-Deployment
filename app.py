import streamlit as st


def main() -> None:
    st.title("First Streamlit App")
    st.write("This is a simple Streamlit app created for the project.")

    name = st.text_input("Enter your name hello", "World")
    temperature = st.slider("Choose a temperature", 0, 100, 25)

    if st.button("Greet"):
        st.success(f"Hello, {name}! The selected temperature is {temperature}.")

    st.caption("Built with Streamlit")


if __name__ == "__main__":
    main()
