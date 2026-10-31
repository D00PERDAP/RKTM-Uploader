import sys
from ui import App
App('settings' if '--admin' in sys.argv else 'schedule').mainloop()
