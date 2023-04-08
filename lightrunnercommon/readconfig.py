import configparser

def getconfig():
    config_object = configparser.ConfigParser()
    file = open("config.ini","r")
    config_object.read_file(file)
    output_dict=dict()
    sections=config_object.sections()
    for section in sections:
        items=config_object.items(section)
        output_dict[section]=dict(items)
    return output_dict
