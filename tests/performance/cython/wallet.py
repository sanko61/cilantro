import cython
if cython.compiled:
    print("Yep, I'm compiled.")
else:
    print("Just a lowly interpreted script.")

from cilantro.protocol.wallet import *
import time

start = time.time()
for i in range(10000):
    generate_keys()
end = time.time()

print('It took {}s'.format(int(end-start)))
