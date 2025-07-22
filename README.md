# Substack Archiver

Substack Archiver is a Python program that allows users to archive posts from their favorite Substack newsletters. The program saves all posts in HTML, JSON, and plain text formats. It uses Playwright to interact with Substack, ensuring robust and reliable archiving.

![Substack Archiver](README/images/cover.png)

## Features

-   **Archive Multiple Substacks**: Configure a list of Substack publications to archive in a single run.
-   **Incremental Archiving**: The script automatically skips posts that have already been downloaded, saving time and bandwidth.
-   **Multiple Formats**: Saves posts as individual HTML files, JSON data dumps, and clean plain text files.
-   **Login Support**: Can log into your Substack account to access paywalled or private posts.
-   **Persistent Sessions**: Save your login session to avoid re-authenticating on every run.
-   **Works with Custom Domains**: Archives posts from both `substack.com` URLs and custom domains.

## Getting Started

### Prerequisites

-   Python 3.12+
-   [uv](https://github.com/astral-sh/uv) (recommended for installation)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/unchain0/substack_archiver.git
    cd substack_archiver
    ```

2.  **Install dependencies using `uv`:**
    ```bash
    uv pip install -r requirements.txt
    ```

3.  **Install Playwright browsers:**
    ```bash
    playwright install
    ```

### Configuration

1.  **Configure Substacks:**
    Open the `config.json` file and add the Substack publications you want to archive. Use the following format:

    ```json
    {
      "substacks": [
        {
          "name": "example",
          "url": "https://example.substack.com/"
        },
        {
          "name": "customdomain",
          "url": "https://www.customdomain.com/"
        }
      ]
    }
    ```

2.  **Set Up Environment Variables (Optional - for Login):**
    To archive private or paywalled content, you need to provide your Substack credentials.

    Create a file named `.env` in the project root and add your email and password:
    ```
    SUBSTACK_EMAIL="your_email@example.com"
    SUBSTACK_PASSWORD="your_password"
    ```

## Usage

### Running the Archiver

Once you have configured your `config.json` file, run the archiver:

```bash
python substack_archiver.py
```

The script will iterate through the publications in your config file and archive their posts.

### Saving Your Login Session (Optional)

To avoid logging in every time, you can save your session state after a successful login.

1.  Run the `save_session.py` script:
    ```bash
    python save_session.py
    ```
2.  The script will open a Chromium browser. Log in to your Substack account manually.
3.  Once you have logged in, close the browser.
4.  A `storage_state.json` file will be created. The main archiver script will automatically use this file for future runs, bypassing the need for manual login.

## Output

The program saves the archived posts into three directories:

-   `html_dumps/`: Contains the original HTML of each post.
-   `json_dumps/`: Contains the raw JSON data for each post.
-   `text_dumps/`: Contains a clean, readable plain text version of each post.

Each of these directories will have subdirectories corresponding to the `name` you provided in `config.json`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
