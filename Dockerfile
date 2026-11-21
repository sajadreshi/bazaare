# Set base image (host OS)
FROM python:3.12-alpine

# Listen on all interfaces inside the container (server.py defaults to 127.0.0.1).
# SECRET_KEY, DATABASE_URL and ADMIN_* must be passed in at run time.
ENV HOST=0.0.0.0 PORT=8000
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