
config = {
    "inspector":{
        "outdir":"./",
        "csv_name":"stis_archive.csv",
        "gen_csv":True,
        "datatype":"S",
        "instrument":"STIS",
        "stylesheets":['https://codepen.io/chriddyp/pen/bWLwgP.css'],
        "mast":[]
    },
    "modes":{
        "spec_groups": [["G140L", "G140M", "G230M", "G230L"],
                             ["G230LB", "G230MB", "G430L",
                                 "G430M", "G750L", "G750M"],
                             ["E140M", "E140H", "E230M", "E230H"],
                             ["PRISM"]],
        "spec_labels": ["MAMA First Order Spectroscopy",
                             "CCD First Order Spectroscopy",
                             "MAMA Echelle Spectroscopy",
                             "MAMA Prism Spectroscopy"],
        "im_groups": [["MIRVIS", "MIRNUV", "MIRFUV"]],
        "im_labels": ["Imaging"]
    },
    "apertures":{
        "groups": [["52X0.05", "52X0.1", "52X0.2", "52X0.5", "52X2"],
                            ["31X0.05NDA", "31X0.05NDB", "31X0.05NDC"],
                            ["6X6", "0.5X0.5", "2X2", "0.1X0.03", "0.1X0.06", "0.1X0.09", "0.1X0.2",
                             "0.2X0.06", "0.2X0.09", "0.2X0.2", "0.2X0.5", "0.3X0.06", "0.3X0.09", "0.3X0.2", "1X0.06",
                             "1X0.2", "6X0.06", "6X0.2", "6X0.5", "0.2X0.05ND", "0.3X0.05ND"],
                            ["25MAMA", "50CCD", "50CORON"],
                            ["F25QTZ", "F25SRF2"],
                            ["F25ND3", "F25ND5", "F25NDQ1",
                             "F25NDQ2", "F25NDQ3", "F25NDQ4"],
                            ["F25MGII", "F25CN270", "F25CIII", "F25CN182", "F25LYA"]],
        "labels": ["Long Slits", "Neutral-Density-Filtered Long Slits",
                            "Square Apertures", "Full-Field Clear Apertures",
                            "FUV-MAMA Longpass", "Neutral Density Filters (MAMA)", "Narrow-Band"]
    }
}
