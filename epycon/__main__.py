if __name__ == "__main__":
    import os
    import sys
    import json
    import logging
    import jsonschema

    from epycon.core._validators import _validate_path
    from epycon.core.helpers import default_log_path, deep_override, difftimestamp
    from epycon.cli import batch

    config_path = os.environ.get("EPYCON_CONFIG", os.path.join(os.path.dirname(__file__), 'config', 'config.json'))
    jsonschema_path = os.environ.get("EPYCON_JSONSCHEMA", os.path.join(os.path.dirname(__file__), 'config', 'schema.json'))

    # Instantiate basic logger
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=default_log_path(),
        filemode="w",
    )
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    
    # Parse CLI arguments
    args = batch.parse_arguments()
    
    # Validate custom config path if provided
    if args.custom_config_path:        
        config_path = _validate_path(args.custom_config_path)

       
    # Load JSON configuration
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Override config with custom CLI arguments if provided        
    overrides = {
        "paths.input_folder": args.input_folder,
        "paths.output_folder": args.output_folder,
        "paths.studies": args.studies,
        "data.output_format": args.output_format,
        "entries.convert": args.entries,
        "entries.output_format": args.entries_format,
        }
    
    for arg, value in overrides.items():        
        if value is not None:            
            cfg = deep_override(cfg, arg.split("."), value)            


    # Load and validate jsonschema
    try:
        with open(jsonschema_path, "r") as f:
            schema = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {jsonschema_path}")
            
    try:
        jsonschema.validate(cfg, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Invalid config: {e}")
    

    # ----------------------- batch conversion ----------------------
    from glob import iglob

    from epycon.config.byteschema import (
        ENTRIES_FILENAME, LOG_PATTERN
    )

    from epycon.iou import (
        LogParser,
        EntryPlanter,
        CSVPlanter,
        HDFPlanter,
        readentries,
        mount_channels,
    )

    input_folder = _validate_path(cfg["paths"]["input_folder"], name='input folder')
    output_folder = _validate_path(cfg["paths"]["output_folder"], name='output folder')
    valid_studies = set(cfg["paths"]["studies"])
    valid_datalogs = set(cfg["data"]["data_files"])
    output_fmt = cfg["data"]["output_format"]

    for study_path in iglob(os.path.join(input_folder, '**')):
        study_id = os.path.basename(study_path)

        if valid_studies and study_id not in valid_studies:            
            continue
        
        try:
            # make output directory
            os.makedirs(os.path.join(output_folder, study_id), exist_ok=True)
        except OSError as e:
            logger.error(f"Unable to create output folder {study_id} in {output_folder}.")
            continue
    
        # read entries
        if cfg["entries"]["convert"]:
            try:
                entries = readentries(
                    f_path=os.path.join(study_path, ENTRIES_FILENAME),
                    version=cfg["global_settings"]["workmate_version"],
                    )
            except OSError as e:                
                logger.warning(f"Could not find ENTRIES log file. Annotation export will be skipped.")
                entries = list()
        else:
            entries = list()
        
        entryplanter = EntryPlanter(entries)

        if cfg["entries"]["summary_csv"] and entries:
            # create summary csv containing all annotations
            criteria = {
                "fids": cfg["data"]["data_files"],
                "groups": cfg["entries"]["filter_annotation_type"],
                }
            
            entryplanter.savecsv(
                os.path.join(output_folder, study_id, "entries_summary.csv"),                                
                criteria=criteria,
            )

        # iterate over datalog files
        logger.info(f"Converting study {study_id}")
        for datalog_path in iglob(os.path.join(study_path, LOG_PATTERN)):
            datalog_id = os.path.basename(datalog_path).rstrip(".log")

            # check if selection of datafiles exists
            if valid_datalogs and datalog_id not in valid_datalogs:
                # skip conversion if current datalog is not included
                continue

            # open parser contex manager
            print(f"Converting {datalog_id}: ", end="")
            with LogParser(
                datalog_path,
                version=cfg["global_settings"]["workmate_version"],                
                samplesize=cfg["global_settings"]["processing"]["chunk_size"],
            ) as parser:
                # get datalog header
                header = parser.get_header()
                ref_timestamp = header.timestamp

                # create channel mappings
                header.channels.add_custom_mount(cfg["data"]["custom_channels"], override=False)
                if cfg["data"]["leads"] == "computed":
                    # use WM defined electrode mount
                    mappings = header.channels.computed_mappings                    
                else:
                    # use raw unmounted leads
                    mappings = header.channels.raw_mappings

                # filter out channels not specified by user from mappings
                if cfg["data"]["channels"]:
                    valid_channels = set(cfg["data"]["channels"])
                    mappings = {key: value for key, value in mappings.items() if key in valid_channels}

                # instantiate planter and write data chunks
                column_names = list(mappings.keys())

                if output_fmt == "csv":
                    DataPlanter = CSVPlanter
                elif output_fmt == "h5":                    
                    DataPlanter = HDFPlanter
                else:
                    raise ValueError
                
                # instantiate planter with coversion factor for HDF of 1000 -> uV to mV
                with DataPlanter(
                    os.path.join(output_folder, study_id, datalog_id + "." + output_fmt),
                        column_names=column_names,
                        sampling_freq=header.amp.sampling_freq,
                        factor=1000,
                        units="mV",
                ) as planter:
                    # create mandatory datasets
                    

                    # iterate over chunks of data and write to disk
                    for chunk in parser:                        
                        # compute leads                        
                        chunk = mount_channels(chunk, mappings)                                                
                        planter.write(chunk)

                    # write entries to hdf file
                    if cfg["data"]["pin_entries"] and hasattr(planter, "add_marks"):
                        # convert timestamps -> datetimediff -> samples
                        if entries:
                            groups, positions, messages = zip(
                                *[(
                                    e.group,
                                    header.amp.sampling_freq*difftimestamp((e.timestamp, ref_timestamp)),
                                    e.message,
                                    ) for e in entries if e.fid == datalog_id
                                    ])
                            # write marks
                            planter.add_marks(
                                positions=positions,
                                groups=groups,
                                messages=messages,
                                )
                            print()
            # convert and store entries | csv or sel per each file            
            if cfg["entries"]["convert"] and entries:                
                criteria = {
                    "fids": [datalog_id],
                    "groups": cfg["entries"]["filter_annotation_type"],
                }                
                file_fmt = cfg["entries"]["output_format"]
                
                if file_fmt == "csv":
                    # store as .csv file
                    entryplanter.savecsv(
                        os.path.join(output_folder, study_id, datalog_id + "." + file_fmt),
                        criteria=criteria,
                        ref_timestamp=ref_timestamp,
                    )
                elif file_fmt == "sel":
                    # store as SignalPlant .sel text file
                    entryplanter.savesel(
                        os.path.join(output_folder, study_id, datalog_id + "." + file_fmt),
                        ref_timestamp,
                        header.amp.sampling_freq,
                        list(mappings.keys()),
                        criteria=criteria,                        
                    )
                else:
                    pass

            print(f"DONE")

