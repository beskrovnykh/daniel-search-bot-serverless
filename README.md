# Daniel Zuev Telegram Search Bot V2 in AWS Lambda

This project implements semantic search of excerpts from Daniil Zuev's satsangs. Users can send text queries or voice messages, and the bot will provide relevant excerpts from the satsangs in response.

## Technologies

- [OpenAI](https://openai.com/)
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [Chalice](https://chalice.readthedocs.io/)
- [Pinecone](https://www.pinecone.io/)

## Local Setup

Before starting, make sure all required dependencies are installed. Then follow the steps:

1. Install Python using pyenv or your preferred Python installation method.
2. Create a virtual environment: `python3 -m venv .venv`.
3. Activate your virtual environment: `source .venv/bin/activate`.
4. Install dependencies: `pip install -r requirements.txt`.
5. Configure your credentials in a new copy of `config.json.template` named `config.json` and add all your environment variables there.

```shell
$ chalice local --stage=local
```

## Deployment

For deploying the application to AWS, execute the following command:

```shell
$ chalice deploy --stage=prod --connection-timeout 900
```

## Setting up the Webhook

To set up the Webhook for your bot, execute the following command. Be sure to change the URL to your web address:

```shell
$ chmod +x set_webhook
$ ./set_webhook https://6444-2001-448a-5066-346f-b9e4-39d2-16d5-2209.ap.ngrok.io
```

## License

This project is licensed under the terms of the MIT license.

## Contact

If you have any questions or suggestions, feel free to reach out.