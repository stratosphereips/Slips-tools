# Slips Dataset Generator

## Overview

`generate_dataset.sh` is a comprehensive tool that generates structured JSON datasets from Slips network security logs with multi-perspective AI analysis. The script processes Slips evidence logs through the DAG generator and enriches each security alert with three types of expert analysis: behavioral explanation, cause analysis, and risk assessment.

## Features

- **Automated DAG Processing**: Executes `slips_dag_generator.py` in per-analysis mode for structured alert extraction
- **Multi-Input Support**: Handles both raw Slips logs and pre-processed DAG output
- **AI-Enhanced Analysis**: Generates three specialized analyses per alert using LLM models
- **Dual Output Formats**: Produces both JSON datasets and human-readable text reports
- **Robust Parsing**: Correctly handles multi-line analysis blocks with complete evidence preservation

## Usage

### Basic Syntax
```bash
./generate_dataset.sh <input_file> <output.json> [options]
```

### Arguments
- `input_file`: Path to Slips evidence log file or pre-processed DAG output
- `output.json`: Path for the generated JSON dataset

### Options
- `--model MODEL`: LLM model to use (default: `gpt-4o-mini`)
- `--base-url URL`: LLM API base URL (default: `https://api.openai.com/v1`)
- `--text-output FILE`: Generate additional human-readable text report
- `--help`: Display usage information

## Examples

### Generate Dataset from Raw Slips Log
```bash
# Basic dataset generation
./generate_dataset.sh sample_logs/slips.log dataset.json

# With text report
./generate_dataset.sh sample_logs/slips.log dataset.json --text-output report.txt

# Using custom model
./generate_dataset.sh sample_logs/slips.log dataset.json --model gpt-4
```

### Process Pre-formatted DAG Output
```bash
# Direct processing of DAG output
./generate_dataset.sh dag_output.log processed_dataset.json
```

## Output Formats

### JSON Dataset Structure
```json
{
  "dataset": [
    {
      "alert_id": 1,
      "evidence": "Complete multi-line analysis block with:\n- IP and analysis info\n- Timewindow details\n- Network behavior evidence\n- Event counts",
      "behavior_explanation": "Technical analysis of observed network behavior",
      "cause_analysis": "Investigation of possible root causes and attack vectors",
      "risk_assessment": "Threat level evaluation and business impact assessment"
    }
  ]
}
```

### Text Report Format
- Professional security analysis report
- Structured sections for each alert
- Complete evidence details
- Three analysis perspectives per alert
- Executive summary with alert counts and metadata

## Analysis Types

### 1. Behavior Explanation
- **Purpose**: Technical description of observed network activities
- **Focus**: Network protocols, communication patterns, traffic anomalies
- **Audience**: Security analysts and incident responders

### 2. Cause Analysis
- **Purpose**: Investigation of potential root causes
- **Focus**: Attack vectors, legitimate scenarios, common threat patterns
- **Approach**: Balanced analysis covering both malicious and benign possibilities

### 3. Risk Assessment
- **Purpose**: Threat level evaluation and business impact
- **Components**: Risk level (Critical/High/Medium/Low), business impact, investigation priority
- **Output**: Actionable recommendations for security teams

## Prerequisites

### Environment Setup
```bash
# Activate conda environment with required dependencies
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate agents
```

### Required Dependencies
- **Python 3.6+**: For script execution and DAG generation
- **jq**: JSON processing for text output generation
- **slips_dag_generator.py**: Core DAG generation tool
- **stream_query_llm_long_prompt.py**: LLM query interface
- **OpenAI API access**: Via `.env` file with `OPENAI_API_KEY`

### Directory Structure
```
alert_summary/
├── generate_dataset.sh              # Main script
├── slips_dag_generator.py           # DAG generator
├── ../benchmark_models/
│   └── stream_query_llm_long_prompt.py  # LLM interface
└── sample_logs/                     # Test data
    ├── slips.log                    # Raw Slips evidence log
    └── *.log                        # Additional test files
```

## Input File Types

### Raw Slips Evidence Logs
- **Format**: Standard Slips log output with evidence sections
- **Processing**: Automatic DAG generation in per-analysis mode
- **Example**: `sample_logs/slips.log`

### Pre-processed DAG Output
- **Format**: Multi-line analysis blocks separated by `============================================================`
- **Processing**: Direct parsing without DAG generation
- **Detection**: Automatic based on separator presence

### Expected DAG Format
```
192.168.1.113 - Analysis 1 (2023/11/03 23:27:49.132500)
Timewindow: 1970/01/01 00:00:19 to 1970/01/01 01:00:19
• 23:27 - Port scans: 8080/TCP→6, 443/TCP→30, 443/TCP→20 (max: 45 hosts)
• Evidence: 11 events in analysis
============================================================
192.168.1.113 - Analysis 1 (2023/11/03 23:27:53.206763)
...
```

## Performance Considerations

### Processing Time
- **LLM Calls**: 3 API calls per alert (behavior, cause, risk analysis)
- **Large Datasets**: 130 alerts = 390 API calls (estimate 15-30 minutes)
- **Rate Limiting**: Dependent on OpenAI API limits

### Resource Usage
- **Memory**: Scales with alert count and evidence size
- **Storage**: JSON output typically 10-50KB per alert
- **Network**: API bandwidth for LLM queries

## Error Handling

### Common Issues
- **Missing API Key**: Script validates `OPENAI_API_KEY` via dotenv
- **Invalid Log Format**: Graceful handling of unsupported formats
- **LLM API Failures**: Individual query error handling with informative messages
- **Empty Datasets**: Proper handling of logs with no security evidence

### Troubleshooting
```bash
# Test DAG generator directly
python3 slips_dag_generator.py sample_logs/slips.log --per-analysis --minimal

# Verify LLM connectivity
python3 ../benchmark_models/stream_query_llm_long_prompt.py --prompt "test" --model gpt-4o-mini

# Check dependencies
jq --version
conda list | grep openai
```

## Integration Examples

### Batch Processing
```bash
# Process multiple log files
for log in sample_logs/*.log; do
    output="datasets/$(basename "$log" .log)_dataset.json"
    ./generate_dataset.sh "$log" "$output"
done
```

### Pipeline Integration
```bash
# Slips analysis → Dataset generation → Further processing
slips -f network.pcap -o evidence.log
./generate_dataset.sh evidence.log security_dataset.json
python3 ml_training.py security_dataset.json
```

## Security Considerations

- **Defensive Tool**: Designed for legitimate security analysis and research
- **Data Sensitivity**: Generated datasets may contain network security information
- **API Security**: Ensure secure handling of OpenAI API keys
- **Log Sanitization**: Sample logs are from controlled research environments

## Contributing

When extending the script:
1. Maintain the three-analysis structure (behavior, cause, risk)
2. Preserve multi-line evidence block integrity
3. Follow existing error handling patterns
4. Update documentation for new features

## Version History

- **v1.0**: Initial implementation with basic JSON dataset generation
- **v1.1**: Added multi-line parsing support and text output functionality
- **v1.2**: Enhanced error handling and input format detection

## License

Part of the slips-tools repository for network security analysis and research.