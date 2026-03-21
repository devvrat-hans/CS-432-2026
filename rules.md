### ✅ Task: Mandatory Interactive Loop with User Feedback

1. **Check if `userinput.py` exists** in the root directory.

   * If it does not exist, create it with:

     ```python
     # userinput.py
     user_input = input("prompt: ")
     ```

2. **Loop Contract (must run every time for validation-loop testing)**:

   * Run the assigned task for the current iteration.
    * Then run **only** this exact command (no piping, no `printf`, no heredoc, no extra shell wrappers):

     ```bash
     python3 userinput.py
     ```

    * ❌ Do **not** run commands like:

       ```bash
       printf 'success-plan\n' | python3 userinput.py
       ```

    * ✅ The input must be typed interactively after the prompt appears in the terminal.

   * Terminal must be in the chat window.
   * Read the entered value and branch exactly as follows:
     * If input is `stop`: terminate immediately.
     * Otherwise: treat input as the next instruction and continue.
   * After completing that instruction, run `python3 userinput.py` again.
   * Keep repeating this cycle until `stop` is received.

3. **Validation Loop Test Requirement (non-optional)**:

   * For validation-loop feature work, do not stop after one pass.
   * Continue iterative cycles to test multiple scenarios (pass, fail, auto-fix, retry-limit behavior) until user enters `stop`.

4. **Output Discipline**:

   * Keep each iteration focused on execution and result.
   * Do not create separate summary/documentation files unless explicitly asked.

5. **File Writing Method (mandatory)**:

   * When editing or creating files, **ALWAYS** use direct file manipulation tools (like `replace_string_in_file` or `create_file`) whenever possible.
   * **NEVER** use heredoc or similar inline shell redirection methods for writing files under any circumstances.
   * Only as an absolute last resort (if direct tools fail or are unavailable), create a temporary `.py` script to generate the file, execute it, and then clean it up. But direct editing is always the priority.

6. **Iterative Loop Discipline**:

   Also make sure that you run iterative loop after completing and acting on all the instructions in the current iteration. Do not run iterative loop in the middle of executing instructions of current iteration. Run it only after completely finishing all the instructions of current iteration.