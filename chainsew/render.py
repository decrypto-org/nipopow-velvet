from graphviz import Digraph

def render(blocks, show_interlinks=True, show_thorny_interlinks=True, show_id=False, scale_superblocks=True):
    ids = set([b.id for b in blocks])
    dot = Digraph(comment='Execution')
    dot.graph_attr['rankdir'] = 'LR'
    dot.attr('edge', dir='back')
    with dot.subgraph(name='cluster_0') as c:
        c.graph_attr['rank'] = 'lr'
        for block in blocks:
            c.attr('node', shape='square')
            if block.genesis:
                c.attr('node', peripheries='2')
                c.node(str(block.id), 'G')
            else:
                c.attr('node', peripheries='1')
                if block.adversarial:
                    c.attr('node', fillcolor='black', style='filled', fontcolor='white')
                else:
                    c.attr('node', fillcolor='white', style='filled', fontcolor='black')
                if scale_superblocks:
                    c.attr('node', height=str(block.level / 2), fontsize=str(12 + 8*block.level))
                label = str(block.level)
                if show_id:
                    label += '\n' + '(' + str(block.id) + ')'
                c.node(str(block.id), label)
        for block in blocks:
            if block.prev is not None:
                assert block.prev.id in ids, 'Previd pointer to missing block'
                c.edge(str(block.prev.id), str(block.id))
            if show_interlinks:
                for pointer in set(block.velvet_interlink):
                    assert pointer.id in ids, 'Interlink pointer to missing block'
                    c.edge(str(pointer.id), str(block.id), style='dashed')
            if show_thorny_interlinks and block.thorny:
                for pointer in set(block.velvet_interlink):
                    assert pointer.id in ids, 'Thorny interlink pointer to missing block'
                    c.edge(str(pointer.id), str(block.id), style='dashed')
    dot.view()
