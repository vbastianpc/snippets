'''
Este script agrega play-and-pause a una playlist .xspf de VLC existente.
De esta manera, VLC siempre pausará en el último fotograma, sin importar la configuración que tenga.

python playlist_play_and_pause.py <playlist_path>
'''


import sys
from os.path import dirname, basename, splitext, join, isfile
import xml.etree.ElementTree as ET


playlist_paths = [arg for arg in sys.argv[1:] if isfile(arg) and arg.endswith('.xspf')]

ns = {
    'default': 'http://xspf.org/ns/0/',
    'vlc': 'http://www.videolan.org/vlc/playlist/ns/0/',
}
ET.register_namespace('', ns['default'])
ET.register_namespace('vlc', ns['vlc'])


def add_play_and_pause(file):
    tree = ET.parse(file)
    root = tree.getroot()
    trackList = root.find('default:trackList', ns)
    edited = False
    for track in trackList.findall('default:track', ns):
        for extension in track.findall('default:extension', ns):
            if not any([item.text == 'play-and-pause' for item in extension.findall('vlc:option', ns)]):
                ET.SubElement(extension, f'{{{ns["vlc"]}}}option').text = 'play-and-pause'
                edited = True
    if edited:
        output = join(
            dirname(file),
            splitext(basename(file))[0] + ' - PLAY AND PAUSE.xspf'
        )
        ET.ElementTree(root).write(
            output,
            xml_declaration=True,
            encoding='utf-8',
            method='xml',
        )
        return output

outputs = list(map(add_play_and_pause, playlist_paths))
