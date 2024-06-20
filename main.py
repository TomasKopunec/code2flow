from code2flow.engine import code2flow, LanguageParams, SubsetParams
import subprocess

def convert_dot_to_png(input_dot_file, output_png_file):
    try:
        # Run the dot command
        subprocess.run(['dot', '-Tpng', input_dot_file, '-o', output_png_file], check=True)
        # Remove the file
        subprocess.run(['rm', input_dot_file], check=True)
        print(f"Successfully converted {input_dot_file} to {output_png_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while converting {input_dot_file} to {output_png_file}: {e}")
    except FileNotFoundError:
        print("Graphviz not installed or not found in PATH")

project_path = './projects/simple'

code2flow(
    project_path,
    output_file='./output/graph.json'
)
code2flow(
    project_path,
    output_file='./output/graph.dot'
)
convert_dot_to_png('./output/graph.dot', './output/graph.png')