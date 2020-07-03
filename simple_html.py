from html.parser import HTMLParser


class Tag:
    def __init__(self, tag=None, attrs=(), is_self_closing=None):
        self.type = tag
        self.is_self_closing = is_self_closing
        self._attrs = tuple(attrs)
        self._content = tuple()
        
    @property
    def attrs(self):
        """returns dict of Tag's attrs"""
        return dict(self._attrs)

    @property
    def text(self):
        """returns str of all contained text"""
            
        return ''.join(c if isinstance(c, str) else c.text for c in self._content)

    def _add_content(self, obj):
        if isinstance(obj, (Tag, str)):
            self._content += (obj,)
        else:
            raise TypeError('Argument must be str or %s, not %s' % (self.__class__, obj.__class__))

    def find(self, tag=None, attrs=None):
        """returns Tag or None"""

        return next(self._find_all(tag, attrs), None)

    def find_all(self, tag=None, attrs=None):
        """returns list"""

        return list(self._find_all(tag, attrs))
        
    def _find_all(self, tag_type=None, attrs=None):
        """returns generator"""

        if not (isinstance(tag_type, (str, Tag)) or tag_type is None):
            raise TypeError('tag_type argument must be str or Tag, not %s' % (tag_type.__class__))

        if not (isinstance(attrs, dict) or attrs is None):
            raise TypeError('attrs argument must be dict, not %s' % (self.__class__))

        # get tags-descendants generator
        results = self.descendants

        # filter by Tag.type
        if tag_type:
            if isinstance(tag_type, Tag):
                tag_type, attrs = tag_type.type, (attrs if attrs else tag_type.attrs)

            results = filter(lambda t: t.type == tag_type, results)

        # filter by Tag.attrs
        if attrs:
            # remove Tags without attrs
            results = filter(lambda t: t._attrs, results)

            def filter_func(tag):
                for key in attrs.keys():
                    if attrs[key] not in tag.attrs.get(key, ()):
                        return False
                return True
            
            # filter by attrs
            results = filter(filter_func, results)
        
        yield from results

    @property
    def children(self):
        """returns generator of tags-children"""

        return (obj for obj in self._content if isinstance(obj, Tag))

    @property
    def descendants(self):
        """returns generator of tags-descendants"""

        for child_tag in self.children:
            yield child_tag
            yield from child_tag.descendants

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        if not attr.startswith("__"):
            return self.find(tag=attr)

    def __repr__(self):
        attrs = ' '.join(str(k) if v is None else '{}="{}"'.format(k, v) for k, v in self._attrs)
        starttag = ' '.join((self.type, attrs)) if attrs else self.type

        if self.is_self_closing:
            return '<{starttag}>\n'.format(starttag=starttag)
        else:
            nested = '\n' * bool(next(self.children, None)) + ''.join(map(str, self._content))
            return '<{}>{}</{}>\n'.format(starttag, nested, self.type)

            
class Parser(HTMLParser):
    def __init__(self, html_code, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._root = Tag('_root')
        self._path = [self._root]
        
        self.feed(''.join(map(str.strip, html_code.splitlines())))
        self.handle_endtag(self._root.type)
        self.close()

        self.find = self._root.find
        self.find_all = self._root.find_all

    @property
    def attrs(self):
        return self._root.attrs

    @property
    def text(self):
        return self._root.text

    def handle_starttag(self, tag, attrs):
        self._path.append(Tag(tag=tag, attrs=attrs))

    def handle_endtag(self, tag_type):
        for pos, tag in tuple(enumerate(self._path))[::-1]:
            if isinstance(tag, Tag) and tag.type == tag_type and tag.is_self_closing is None:
                tag.is_self_closing = False

                for obj in self._path[pos + 1:]:
                    if isinstance(obj, Tag) and obj.is_self_closing is None:
                        obj.is_self_closing = True

                    tag._add_content(obj)

                self._path = self._path[:pos + 1]

                break

    def handle_startendtag(self, tag, attrs):
        self._path.append(Tag(tag=tag, attrs=attrs, is_self_closing=True))

    def handle_decl(self, decl):
        self._path.append(Tag(tag='!'+decl, is_self_closing=True))

    def handle_data(self, text):
        self._path.append(text)

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        if not attr.startswith("__"):
            return getattr(self._root, attr)

    def __repr__(self):
        return ''.join(str(c) for c in self._root._content)
