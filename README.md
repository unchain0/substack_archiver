# Substack Archiver

Substack Archiver is a simple Python program that allows users to archive the contents of their Substack newsletter. The program saves all the contents in a separated HTML file and also creates multiple JSON dumps. It is important to note that the HTML is raw, without any CSS or JS. It just provides a basic structure for reading the content. However you can use the [Firefox Reader Viewer](https://support.mozilla.org/en-US/kb/firefox-reader-view-clutter-free-web-pages) or Chromes Reader Mode, to get 
a pretty view of the webcontent.
Note that direct video or audio files from Substack are not supported yet. 

![Substack Archiver](README/images/cover.png)


## Getting Started

To use Substack Archiver, you will need to fill out the "config.env" file with your Substack login information. Once you have done this, you will need to install the requirements by running the following command:

```
pip install -r requirements.txt
```

To run the **Substack Archiver**, simply enter the following command in your terminal:

```
python substack_archiver.py "substack_name" "url_of_substack"
```

## TODO
- [ ] Add support for audio files
- [ ] Add support for video files

## Output

The program will save each Substack post in a separated HTML file and also create multiple JSON dumps. The HTML files will contain all the articles, images, and other content from your Substack newsletter. The JSON dumps will contain metadata such as the title, date, author, and tags for each article.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
