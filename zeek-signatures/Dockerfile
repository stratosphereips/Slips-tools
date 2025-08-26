FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    software-properties-common \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Add Zeek repository
RUN wget -qO - https://download.opensuse.org/repositories/security:zeek/xUbuntu_22.04/Release.key | apt-key add - && \
    echo 'deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_22.04/ /' | tee /etc/apt/sources.list.d/security:zeek.list

# Install Zeek
RUN apt-get update && apt-get install -y zeek && rm -rf /var/lib/apt/lists/*

# Set PATH for Zeek
ENV PATH="/opt/zeek/bin:${PATH}"

# Create working directory
WORKDIR /signatures

# Copy validation script
COPY validate_signature.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/validate_signature.sh

# Default command
CMD ["bash"]