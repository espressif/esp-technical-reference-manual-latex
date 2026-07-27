# Start building the image for TeX Live image
FROM texlive/texlive:TL2024-historic

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y python3 python3-pip python3-venv libfontconfig \
    && rm -rf /var/lib/apt/lists/*

# Increase TeX main memory before dumping formats. Large manuals such as the
# full ESP32-P4 TRM otherwise hit "TeX capacity exceeded [main memory size]" while
# flushing deferred writes (.toc/.lot/.lof via morewrites), which leaves the
# Contents / List of Tables / List of Figures pages empty.
#
# kpathsea honors these environment variables and they override the default
# texmf.cnf (writing only to TEXMFSYSCONFIG is not enough: the dist texmf.cnf
# still wins for kpsewhich). Rebuild only xelatex: this project uses XeLaTeX,
# and fmtutil-sys --all also tries luajit* formats that can fail the build.
ENV main_memory=12000000 \
    extra_mem_top=4000000 \
    extra_mem_bot=4000000
RUN set -eux; \
    fmtutil-sys --byfmt xelatex; \
    test "$(kpsewhich -var-value=main_memory)" = "12000000"

# Create a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN /opt/venv/bin/pip install --upgrade pip

# Copy requirements and install all dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
