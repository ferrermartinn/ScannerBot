class DeltaBandit:
    def __init__(self,*a,**k):
        self.cfg=type('C',(),{'algo':'ucb1','state_path':'bandit_state.json','warmup_pulls':2,'decay_alpha':0.7})()
    def suggest(self,*a,**k):
        class D: pass
        d=D(); d.quoted_price=(a[1] + 0.01) if a[0]=='BUY' else max(0,a[1]-0.01); d.next_review_in_s=45; d.rationale='ok'; return d
    def metrics(self):
        return {'arms':{}}
    def persist(self):
        pass
