import sys
import json
import requests


def generate_plantuml(graph):
    uml = "digraph G {\n"
    for package, deps in graph.items():
        for dep in deps.keys():
            uml += f'"{package}" -> "{dep}";\n'
    uml += "}\n"
    return uml


def get_npm_dependencies(package_name, repurl):
    url = f'{repurl}{package_name}'
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch package data: {response.status_code}")

    package_data = response.json()
    latest_version = package_data['dist-tags']['latest']
    dependencies = package_data['versions'][latest_version].get('dependencies', {})
    return dependencies


def get_transitive_dependencies(package_name, collected, repurl, max_depth):
    max_depth = max_depth - 1
    if (max_depth == 0):
        return
    if package_name in collected:
        return collected
    try:
        dependencies = get_npm_dependencies(package_name, repurl)
        collected[package_name] = dependencies
        for dep in dependencies:
            get_transitive_dependencies(dep, collected, repurl, max_depth)
        return collected
    except Exception as e:
        print(e)
        return collected


def main():
    with open("conf.json", 'r') as config_file:
        config = json.load(config_file)
    #graphviz_path = config['graphviz_path']
    package_path = config['package_path']
    graph_output_path = config['graph_output_path']
    max_depth = config['max_depth']
    repository_url = config['repository_url']
    # Получение всех зависимостей, включая транзитивные:
    all_dependencies = get_transitive_dependencies(package_path, {}, repository_url, max_depth)
    #print(generate_plantuml(all_dependencies))
    with open(graph_output_path, 'w') as f:
        f.write(generate_plantuml(all_dependencies))

if __name__ == '__main__':
    main()