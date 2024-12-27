# JSReport Backup Converter

A simple Python utility to convert JSReport backup files (`.jsexport`) into a single JSON file.

## Description

This tool takes a JSReport backup file (`.jsexport`) and converts it into a consolidated JSON file that can be used for various purposes. It simplifies the process of working with JSReport backup data by providing it in a more accessible format.

## Prerequisites

- Python 3.x

### Required Libraries
All required libraries are part of Python's standard library, so no additional installation is needed:
- `zipfile`: For handling zip file operations
- `json`: For JSON parsing and writing
- `base64`: For base64 encoding/decoding
- `os`: For operating system operations
- `pathlib`: For path manipulations
- `re`: For regular expression operations

## Installation

1. Clone this repository or download the `main.py` file
2. No additional dependencies are required

## Usage

Run the script using Python 3 with the following command structure:

```bash
python3 main.py <input_file> <output_file>
```

### Parameters:

- `<input_file>`: Path to your JSReport backup file (`.jsexport`)
- `<output_file>`: Desired path and name for the output JSON file

### Example:

```bash
python3 main.py export.jsexport output.json
```

This command will:
1. Read the JSReport backup file named `export.jsexport`
2. Convert it to a single JSON file
3. Save the result as `output.json`

## Notes

- Make sure you have read permissions for the input file and write permissions for the output directory
- The tool will overwrite the output file if it already exists

## Error Handling

The script will display appropriate error messages if:
- The input file doesn't exist
- The input file is not readable
- The output directory is not writable
- The input file is not a valid JSReport backup file