# Set base image (host OS)
FROM python:3.12-alpine

# By default, listen on port 5000
EXPOSE 8000/tcp

# Set the working directory in the container
WORKDIR /bazaare

RUN apk add -u zlib-dev jpeg-dev gcc musl-dev

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Specify the command to run on container start
CMD [ "python", "./server.py" ]