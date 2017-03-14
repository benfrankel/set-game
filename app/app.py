import os.path
import json

import pygame
import pygame.freetype

from .gui import window


pygame.freetype.init()


def load_json(filename):
    with open(filename + '.json') as f:
        return json.load(f)


class AppDirectory:
    def __init__(self, name):
        self.root_dir = os.path.join('appdata', name)
        self.dirs = dict()

    def get_path(self, dir_, name):
        return os.path.join(self.root_dir, self.dirs[dir_], name)

    def load(self):
        filename = os.path.join(self.root_dir, 'dir.json')
        with open(filename) as f:
            dir_json = json.load(f)
        for name, path in dir_json.items():
            self.dirs[name] = os.path.join(*path.split('/'))


class AppResources:
    def __init__(self, directory):
        self.directory = directory

        self.images = dict()
        self.fonts = dict()
        self.audio = dict()

    def load_fonts(self, info):
        for name, filename in info.items():
            try:
                font = pygame.freetype.Font(self.directory.get_path('fonts', filename))
            except OSError:
                print('Unable to load font:', filename)
                exit()
            else:
                self.fonts[name] = font

    def load_images(self, info):
        for name, filename in info.items():
            try:
                image = pygame.image.load(self.directory.get_path('images', filename))
            except OSError:
                print('Unable to load image:', filename)
                exit()
            else:
                self.images[name] = image

    # TODO: def load_audio(self, info)

    def load(self):
        self.load_fonts(load_json(self.directory.get_path('info', 'fonts')))
        self.load_images(load_json(self.directory.get_path('info', 'images')))


class AppConfig:
    def __init__(self, directory, resources):
        self.directory = directory
        self.resources = resources

        self.style = None
        self.options = None
        self.controls = None

        # Style building
        self.style_packs = dict()
        self.compose_style = lambda foundation: None

    def load(self):
        # Resource aliases
        self.load_resource_aliases(load_json(self.directory.get_path('config', 'resources')))

        # Configuration
        self.controls = self.load_controls(load_json(self.directory.get_path('config', 'controls')))
        self.options = self.load_options(load_json(self.directory.get_path('config', 'options')))
        self.style = self.load_style(load_json(self.directory.get_path('config', 'style')))
        self.compose_style(self)

    def load_resource_aliases(self, info):
        for resource, aliases in info.items():
            if resource == 'fonts':
                for alias, origin in aliases.items():
                    self.resources.fonts[alias] = self.resources.fonts[origin]
            elif resource == 'images':
                for alias, origin in aliases.items():
                    self.resources.images[alias] = self.resources.images[origin]
            elif resource == 'audio':
                for alias, origin in aliases.items():
                    self.resources.audio[alias] = self.resources.audio[origin]

    def load_style(self, info):
        result = dict()
        for category, names in info.items():
            for name, attrs in names.items():
                if name not in result:
                    result[name] = dict()
                    result[name][category] = dict()
                elif category not in result[name]:
                    result[name][category] = dict()
                for attr_name, attr_value in attrs.items():
                    value = attr_value
                    if attr_value[0] == '@':
                        value = self.style_packs[attr_value[1:]][attr_name]
                    elif attr_value[0] == '$':
                        if attr_value.startswith('$font='):
                            value = self.resources.fonts[attr_value[6:]]
                        elif attr_value.startswith('$image='):
                            value = self.resources.images[attr_value[7:]]
                        elif attr_value.startswith('$audio='):
                            value = self.resources.audio[attr_value[7:]]
                    result[name][category][attr_name] = value
        return result

    def load_options(self, info):
        result = dict()
        for category, names in info.items():
            for name, attrs in names.items():
                if name not in result:
                    result[name] = dict()
                    result[name][category] = dict()
                elif category not in result[name]:
                    result[name][category] = dict()
                for attr_name, attr_value in attrs.items():
                    result[name][category][attr_name] = attr_value
        return result

    def load_controls(self, info):
        result = dict()
        for category, controls in info.items():
            if category not in result:
                result[category] = dict()
            for name, keys in controls.items():
                for key in keys:
                    result[category][key.lower()] = name
        return result

    def style_get(self, query, name=None, category=None):
        attempts = ('global', 'global'), (name, 'global'), ('global', category),\
                   (name, category),\
                   (name, 'default'), ('default', category), ('default', 'default')
        for try_name, try_category in attempts:
            try:
                return self.style[try_name][try_category][query]
            except KeyError:
                pass
        for try_name, try_category in attempts:
            try:
                return self.style_packs['default'][try_name][try_category][query]
            except KeyError:
                pass
        raise KeyError('Cannot find style \'{}\' for \'{}\' in category \'{}\''.format(query, name, category))

    def options_get(self, query, name=None, category=None):
        attempts = ('global', 'global'), (name, 'global'), ('global', category),\
                   (name, category),\
                   (name, 'default'), ('default', category), ('default', 'default')
        for try_name, try_category in attempts:
            try:
                return self.options[try_name][try_category][query]
            except KeyError:
                pass
        raise KeyError('Cannot find option \'{}\' for \'{}\' in category \'{}\''.format(query, name, category))

    def controls_get(self, query, category=None):
        attempts = 'global', category, 'default'
        for try_category in attempts:
            try:
                return self.controls[try_category][query]
            except KeyError:
                pass
        raise KeyError('Cannot find command for key \'{}\' in category \'{}\''.format(query, category))

    def style_add(self, query, name, category, value):
        if name not in self.style:
            self.style[name] = dict()
            self.style[name][category] = dict()
        elif category not in self.style[name]:
            self.style[name][category] = dict()
        self.style[name][category][query] = value


class AppManager:
    def __init__(self, name):
        self.name = name
        self._loaded = False

        # Shared data
        self.directory = AppDirectory(self.name)
        self.resources = AppResources(self.directory)

        # Style building
        self.style_packs = None
        self.compose_style = lambda config: None

        self.setup = lambda root: None

    def load(self):
        self.directory.load()
        self.resources.load()

        self._loaded = True

    def launch(self):
        if not self._loaded:
            raise RuntimeError('Cannot launch app \'{}\' without loading its manager first'.format(self.name))
        app = App(self)
        self.setup(app)
        return app


class App(window.Window):
    def __init__(self, manager, **kwargs):
        self.directory = manager.directory
        self.resources = manager.resources

        self.config = AppConfig(self.directory, self.resources)
        self.config.style_packs = manager.style_packs
        self.config.compose_style = manager.compose_style
        self.config.load()

        super().__init__(self.config.options_get('size', 'window'), **kwargs)

        self.app = self
