from os import getenv
from dotenv import load_dotenv

load_dotenv()

rsmBaseUrl = 'https://api.business.govt.nz/gateway/radio-spectrum-management/v1'

rsmHeaders ={'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': getenv('RSM_SECRET')}

rsmDelay = int(getenv('RSM_DELAY'))