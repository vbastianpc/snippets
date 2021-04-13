'''
Este script creará una playlist de VLC a partir de un video con capítulos (marcadores).

Modo de uso:
python3 create_playlist_from_video_with_chapters.py <video_path> [--tree]

Debido a que VLC mostrará el título del video original en vez del título definido en la playlist, 
me veo obligado a borrar el título video original (metadatos)


Si no quieres borrar el título del video original, puedes usar la opcion '--tree'.
(Se crearán nodos desplegables en la playlist para ver el nombre del capítulo.
Debes activar -> VLC - Preferencias - Lista de repr. - Mostrar árbol de la lista...)

Podrás ver la duración de cada capítulo en el campo 'Descripción' dentro de la playlist de VLC.
'''

import sys
import os
from subprocess import run
import shlex
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom


NS = "http://xspf.org/ns/0/"
NS_VLC = "http://www.videolan.org/vlc/playlist/ns/0/"


def create_playlist(title, tracks, tree=False):
    ET.register_namespace('', NS)
    ET.register_namespace('vlc', NS_VLC)
    playlist = ET.Element('playlist', {'version': '1'})
    ET.SubElement(playlist, f'{{{NS}}}title').text = title
    tracklist = ET.SubElement(playlist, 'trackList')
    for track in tracks:
        tracklist.append(track)
    if tree:
        ext = ET.SubElement(playlist, 'extension', {'application': NS_VLC})
        for track in tracks:
            title = track.find('./title').text
            tid = track.find(f'./extension/{{{NS_VLC}}}id').text
            node = ET.Element(f'{{{NS_VLC}}}node', {'title': title})
            ET.SubElement(node, f'{{{NS_VLC}}}item', {'tid': tid})
            ext.append(node)
    return playlist


def track_creator(filepath):
    def create_track(title, start_time, stop_time, track_id):
        track = ET.Element(f'track')
        ET.SubElement(track, f'location').text = f'file://{filepath}'
        ET.SubElement(track, f'title').text = title
        duration = float(stop_time) - float(start_time)
        ET.SubElement(track, 'duration').text = format(duration, '.0f')
        ET.SubElement(track, f'annotation').text = f'{duration // 60 :0>2.0f}:{duration % 60 :0>2.0f}'
        ext = ET.SubElement(track, f'extension', {'application': NS_VLC})
        ET.SubElement(ext, f'{{{NS_VLC}}}id').text = str(track_id)
        ET.SubElement(ext, f'{{{NS_VLC}}}option').text = f'start-time={start_time}'
        ET.SubElement(ext, f'{{{NS_VLC}}}option').text = f'stop-time={stop_time}'
        return track
    return create_track


def get_chapters(video_path):
    cmd = f'ffprobe -v quiet -show_chapters -print_format json "{video_path}"'
    console = run(shlex.split(cmd), capture_output=True)
    return json.loads(console.stdout.decode('utf-8'))['chapters']


def get_title(video_path):
    cmd = f'ffprobe -v quiet -show_format -print_format json "{video_path}"'
    console = run(shlex.split(cmd), capture_output=True)
    try:
        return json.loads(console.stdout.decode('utf-8'))['format']['tags']['title']
    except KeyError:
        return os.path.basename(video_path)


start = lambda chp: chp['start_time']
stop = lambda chp: chp['end_time']
title = lambda chp: chp['tags']['title']


def remove_metadata_title(video_path):
    temp = video_path + '.temp'
    cmd = f'ffmpeg -v error -i "{video_path}" -metadata title= -c copy -f mp4 "{temp}"'
    run(shlex.split(cmd), check=True)
    os.remove(video_path)
    os.rename(temp, video_path)


def main(video, tree):
    output = os.path.join(
        os.path.dirname(video),
        os.path.splitext(
            os.path.basename(video))[0] + ' - PLAYLIST.xspf'
        )
    main_title = get_title(video)
    create_track = track_creator(video)
    tracks = [
        create_track(
            title=title(chp),
            start_time=start(chp),
            stop_time=stop(chp),
            track_id=i
        ) for i, chp in enumerate(get_chapters(video))
    ]
    root = create_playlist(main_title, tracks, tree=tree)
    xmlstr = minidom.parseString(
        ET.tostring(root, xml_declaration=True, method='xml')
    ).toprettyxml(encoding='UTF-8').decode()
    with open(output, 'w') as f:
        f.write(xmlstr)
    if not tree:
        remove_metadata_title(video)
    print('Playlist -->', output)


if __name__ == '__main__':
    try:
        video_path = sys.argv[1]
    except IndexError:
        sys.exit(0)
    if not os.path.isfile(video_path):
        print(f'El archivo {video_path} no existe')
        sys.exit(0)
    try:
        tree = True if sys.argv[2] == '--tree' else False
    except IndexError:
        tree = False
    main(video_path, tree)
    