# Start building the image for TeX Live image
FROM texlive/texlive:TL2024-historic

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y python3 python3-pip python3-venv libfontconfig \
    && rm -rf /var/lib/apt/lists/*

# Generate TeX format files at image build time
RUN fmtutil-sys --all

# Create a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN /opt/venv/bin/pip install --upgrade pip

# Copy requirements and install all dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
