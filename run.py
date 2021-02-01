
from inspector.config import config
from inspector.fetch_metadata import generate_csv_from_mast

if __name__ == '__main__':
    # Read in Config file
    outdir = config['inspector']['outdir']
    csv_name = config['inspector']['csv_name']
    gen_csv = config['inspector']['gen_csv']
    datatype = config['inspector']['datatype']
    instrument = config['inspector']['instrument']
    stylesheets = config['inspector']['stylesheets']
    mast = config['inspector']['mast']


    if gen_csv:
        generate_csv_from_mast(csv_name, outdir, datatype, instrument)
    print("Launching server...")
    from inspector.app import app
    app.run_server(port=5500)
