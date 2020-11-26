#!/usr/bin/python3
"""
This module extends OrderedDict to support multiple levels. In effect a tree of dicts navigable
using a filesystem like syntax.

Each node (dict) in the tree links to its parent and to the top node of the tree, so navigation
can be 'up' to the parent as well as 'down' to the children.

To achoeve this, __getitem__ is redefined to allow filesystem like navigation using '..' and '/'. This does mean
that '/'  and '..' can't be used as part of node names.

In addition next and previous sibling functionality is provided.

Examples:
    node['childx']      - selects the child node named 'childx' of the current node.
    node['../siblingx'] - selects the sibling node named 'siblingx' of the current node - that is the 
                          child node 'siblingx' of the parent of the current node.
"""

from collections import Hashable
from collections import OrderedDict

class Tree_dict(OrderedDict):
    """
    A class that places an object within a tree. Each node is basically a dict (empty for leaf nodes)
    """
    def __init__(self, *, name, parent, app, childdefs=None): # * forces all args to be used as keywords
        """
        Creates a node and links it from the parent (if present)

        name        : a hashable name for the node
        
        parent      : if not None, then the child will be added as an offspring of this parent
        
        app         : the top parent (root node) of the tree, can hold various tree constant info, None only
                      for the root node itself.

        childdefs   : iterable of definitions for child nodes, each to be the kwargs for calling makeChild
        
        raises ValueError is the parent already has a child with this name, or if the name is not Hashable
        """
        assert isinstance(name, Hashable), 'the name given for variable {} is not hashable'.format(name)
        self.name=name
        self.parent=parent
        self.app=self if app is None else app
        if not parent is None:
            assert not self.name in parent, 'the parent %s already has a child %s' % (parent.name, self.name) 
            parent[self.name]=self
        if not childdefs is None:
            for cdef in childdefs:
                self.makeChild(**cdef)
        super().__init__()

    def makeChild(self, _cclass, name, **kwargs):
        """
        default makeChild creates a child with parent and app defined automatically.
        """
        return _cclass(name=name, parent=self, app=self.app, **kwargs)

    def __getitem__(self, nname):
        splitname=nname.split(self.hiernamesep)
        if len(splitname)==1:
            if nname=='..':
                return self.parent
            else:
                try:
                    return super().__getitem__(nname)
                except KeyError:
                    raise KeyError('key %s not found in %s' % (nname, str(self.keys())))
        cnode=self
        for pname in splitname:
            if pname=='':
                cnode=self.app
            elif pname=='..':
                cnode=cnode.parent
            else:
                try:
                    cnode=cnode.__getitem__(pname)
                except KeyError:
                    raise KeyError('key %s not found in %s' % (pname, str(cnode.keys())))
        return cnode

    def nextChild(self, name=None, filter=None, forward=True, wrap=True):
        """
        Returns the child (name and value) after (or before if forward is False) the child named "name" that matches the filter.
        
        Optionally wraps to the beginning if at the end and vice versa if forward is False
        
        returns the first (filtered) child if name is None, or the next sibling unless wrap is False and is is the last /  first child
        """
        ili=[li for li in list(self.items()) if filter is None or filter(li[1])]
        if len(ili)==0:
            return None, None
        if name is None:
            return ili[0] if forward else ili[-1]
        ilk=[i[0] for i in ili]
        ix = ilk.index(name) + (1 if forward else -1)
        if ix >= len(ilk):
            if wrap:
                ix = 0
            else:
                return None, None
        if ix < 0:
            if wrap:
                ix=len(ili)-1
            else:
                return None, None
        return ili[ix]

    hiernamesep='/'

    def getHierName(self):
        """
        returns the hierarchic name of this variable.
        
        Returns a string using hiernamesep to separate each ancestor's name. 
        """
        if self.parent is None:
            return self.name
        else:
            return self.parent.getHierName()+self.hiernamesep+self.name

    def __repr__(self):
        if len(self) == 0:
            return "{} name={}, leaf node".format(self.__class__.__name__, self.name)
        else:
            return "{} name={}, children {}".format(self.__class__.__name__, self.name, list(self.keys()))

    def pretty(self, indent=0, depth=5):
        if len(self)==0 or indent >= depth:
            return '   '*indent+str(self)
        else:
            return '   '*indent+str(self)+'\n'+'\n'.join([c.pretty(indent=indent+1, depth=depth) for c in self.values()])