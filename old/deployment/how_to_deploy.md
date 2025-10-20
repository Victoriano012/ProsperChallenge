Start with
```{bash}
uv sync
```
just in case.

Then we should use
```{bash}
uv run pcc docker build-push
```
but sometimes it doesn't work, then use
```{bash}
sudo docker build -t victoriano012/prosper:latest .
```
in this case, remember to push the Docker image (I do it "manually" from Docker Desktop).

Finally
```{bash}
uv run pcc deploy --no-credentials
```
and the model should be deployed to your pipecat cloud dashboard (sometimes it fails on first trial and then it works).
