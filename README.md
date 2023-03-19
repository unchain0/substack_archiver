# Substack Archiver

Substack Archiver is a simple Python program that allows users to archive the contents of their Substack newsletter. The program saves all the contents in a separated HTML file and also creates multiple JSON dumps. It is important to note that the HTML is raw, without any CSS or JS. It just provides a basic structure for reading the content.
Note that direct videos from Substack are not supported. However, you can use a tool such as [yt-dlp](https://github.com/yt-dlp/yt-dlp/) to download the videos and then embed them in the HTML file.


## Getting Started

To use Substack Archiver, you will need to fill out the "config.env" file with your Substack login information. Once you have done this, you will need to install the requirements by running the following command:

```
pip install -r requirements.txt
```

After you have installed the requirements, you can run the program by executing the following command:

```
python substack_archiver.py
```


## Output

The program will save each Substack post in a separated HTML file and also create multiple JSON dumps. The HTML files will contain all the articles, images, and other content from your Substack newsletter. The JSON dumps will contain metadata such as the title, date, author, and tags for each article.


## Error Handling

Please note that Substack Archiver does not include any error handling. As such, it is important to ensure that your Substack login information is correct and that the program is used in a stable environment.


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.