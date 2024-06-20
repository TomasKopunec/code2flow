from code2flow.engine import code2flow, SubsetParams
import subprocess

project_path = './projects/simple'

# Generates json
code2flow(
    project_path,
    output_file='./output/graph.json'
)

# Generates picture
code2flow(
    project_path,
    output_file='./output/graph.png'
)