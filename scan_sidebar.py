lines=open('frontend/app.py',encoding='utf-8',errors='replace').readlines()
with open('sidebar_locs.txt','w') as f:
    for i,l in enumerate(lines):
        if 'st.sidebar' in l or 'with st.sidebar' in l:
            f.write(f"{i+1}|{l.rstrip()[:100]}\n")
print("done")
