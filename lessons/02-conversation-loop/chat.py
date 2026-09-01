"""A terminal chat that keeps the conversation in a plain list."""
from llm import complete


def main():
    messages = []
    print("Type a message. Press Ctrl+C to leave.")
    while True:
        try:
            user_input = input("\nyou> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user_input.strip():
            continue
        messages.append({"role": "user", "content": user_input})
        reply = complete(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"\nbot> {reply}")


if __name__ == "__main__":
    main()
