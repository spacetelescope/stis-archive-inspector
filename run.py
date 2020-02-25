from inspector.app import app
from inspector.config import config
from inspector.fetch_metadata import generate_csv_from_mast

if __name__ == '__main__':

    if config['inspector']['gen_csv']:
        
        outdir = config['inspector']['outdir']
        csv_name = config['inspector']['csv_name']
        datatype = config['inspector']['datatype']
        instrument = config['inspector']['instrument']
        generate_csv_from_mast(csv_name, outdir, datatype, instrument)

    app.run_server(debug=True, port=5500)
