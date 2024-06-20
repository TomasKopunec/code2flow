from code2flow.engine import code2flow

project_path = './projects/simple'

code2flow(
    project_path,
    output_dir='output',
    generate_json=True,
    generate_image=True
)