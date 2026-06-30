# Contributing to ASME B31.8 Pipeline Designer

This project is a collaborative effort to build an expert-assist tool for ASME B31.8 compliance checking. We welcome contributions from experienced pipeline engineers and software developers.

## 🚀 How to Contribute

1.  **Fork the Repository:** Create your own fork of this repository.
2.  **Clone Locally:** Clone your fork to your local machine.
3.  **Create a Branch:** Create a new feature branch: `git checkout -b feature/your-contribution-name`.
4.  **Implement Changes:** Make your desired changes (bug fixes, new features, documentation updates).
5.  **Test Thoroughly:** **Crucially, test your changes against the existing test suite (`tests/`) and manually verify the logic in the UI.**
6.  **Commit & Push:** Commit your changes and push to your branch: `git commit -m "feat: Added description of my change"` followed by `git push origin feature/your-contribution-name`.
7.  **Open a Pull Request (PR):** Open a Pull Request against the `main` branch.

## 🛠️ Development Workflow

### 1. Environment Setup
Follow the setup instructions in the `README.md` file.

### 2. Core Logic Changes (`engine.py`)
*   **Standards Updates:** Any change to ASME code requirements (e.g., new pressure ratings, different safety factors) must be documented here first.
*   **Testing:** Always add unit tests to `tests/test_engine.py` when modifying calculation logic.

### 3. UI/UX Changes (`ui/`)
*   **Streamlit State:** Be mindful of `st.session_state` management. State changes must be predictable.
*   **User Feedback:** Use the `ui_utils.py` functions (`render_trace_block`, etc.) to ensure all technical findings are presented clearly to the user.

## 📝 Documentation Standards

*   **`docs/V3_ANALYSIS.md`**: Update this file whenever the core calculation logic changes, detailing the *why* behind the calculation.
*   **`docs/V3_BACKLOG.md`**: Use this to track features that were requested but not implemented in the current release.

## 🐛 Bug Reporting
When reporting a bug, please provide:
1.  **Steps to Reproduce:** Exact sequence of actions in the UI.
2.  **Expected Result:** What the output *should* be according to the code/standard.
3.  **Actual Result:** What the tool *actually* outputted.
4.  **Relevant Context:** Any relevant data points (P, D, T, etc.) used during the test.