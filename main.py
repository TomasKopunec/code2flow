from code2flow.engine import code2flow

code2flow(
    raw_source_paths='./projects/simple',
    output_dir='output',
    generate_json=True,
    generate_image=True,
    build_cache=True
)