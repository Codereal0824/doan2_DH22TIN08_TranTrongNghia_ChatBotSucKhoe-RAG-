def replace_in_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # We only replace `print(` with `logger.debug(` or `logger.info(` if it's within the class / regular methods
    # For simplicity, we just replace `print(` with `logger.debug(` for anything before `def demo_`.

    parts = content.split("def demo_")

    if len(parts) > 1:
        main_code = parts[0]
        demo_code = "def demo_" + parts[1]

        main_code = main_code.replace('print(', 'logger.debug(')

        new_content = main_code + demo_code
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Modified {file_path}")
    else:
        # Check if there's any print before if __name__ == "__main__":
        main_parts = content.split('if __name__ == "__main__":')
        if len(main_parts) > 1:
            main_code = main_parts[0]
            rest_code = 'if __name__ == "__main__":' + main_parts[1]
            main_code = main_code.replace("print(", "logger.info(")
            new_content = main_code + rest_code
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Modified {file_path}")
        else:
            print(f"Skipped {file_path}")


replace_in_file(r'd:\NAM4_HOC_KY2\Chatbot_suckhoe\backend\rag\retriever.py')
replace_in_file(r'd:\NAM4_HOC_KY2\Chatbot_suckhoe\backend\rag\chain.py')
