# Substack Archiver

Substack Archiver is a Python program that allows users to archive the contents of their Substack newsletter. The program saves all the contents in separate HTML files and also creates multiple JSON dumps. It uses Playwright to interact with the Substack API, making it more resilient to changes in the website's structure.

![Substack Archiver](README/images/cover.png)

## Features

- Archives Substack posts without requiring login
- Bypasses captcha issues
- Saves posts as individual HTML files
- Creates JSON dumps of post data
- Includes links to audio content (no direct download)
- Works with both Substack.com and custom domain newsletters

## Getting Started

To use Substack Archiver, follow these steps:

1. Clone this repository
2. Install the requirements:

```
pip install -r requirements.txt
playwright install
```
3. Update `config.env` accordingly:
```
SUBSTACK_USERNAME=""
SUBSTACK_PASSWORD=""
``` 

4. Run the Substack Archiver:

```
python substack_archiver.py "substack_name" "url_of_substack"
```

Example:
```
python substack_archiver.py "example" "https://example.substack.com/"
```
or for custom domains:
```
python substack_archiver.py "example" "https://newsletter.example.com/"
```

## Output

The program will save each Substack post in a separate HTML file and also create multiple JSON dumps. The HTML files will contain the articles, images, and links to audio content from your Substack newsletter. The JSON dumps will contain metadata such as the title, date, author, and tags for each article.

Note: The HTML is raw, without any CSS or JS. It provides a basic structure for reading the content. You can use the [Firefox Reader View](https://support.mozilla.org/en-US/kb/firefox-reader-view-clutter-free-web-pages) or Chrome's Reader Mode to get a prettier view of the web content.

## TODO
- [ ] Add support for downloading audio files
- [ ] Add support for video files
- [ ] Implement CSS styling for HTML output

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.