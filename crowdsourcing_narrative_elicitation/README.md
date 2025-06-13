# crowdsourcing

## How to run the server

Run the followings
```bash
// enter the folder
cd crowdsourcing_server
// create environment
conda env create -f environment.yml
// activate environment
conda activate crowdsourcing_server
// run the server
python server.py
```

by default the server runs at `localhost:8000/`

if you need to change the default ports, go to `config.toml` and change the sections `server.host` and or `server.port`

You will need to either forward the ports or use other tool, like ngrok in order to visit the server from outside your local computer.

## How to the retrieve data

The data is stored in the file `db.sqlite`. If you need to retrieve easily all the data, with the server running you can visit this url `localhost:8000/get_statistics?session_key=[PROLIFIC_ID` where you replace `[PROLIFIC_ID]` with the correct prolific ID.
Usage of commands like `wget` or `curl` is suggested

## Customizations

In the `config.toml` file you can change `hostname` and `port`
By default the order of pages is `sign_in`, `guidelines` `example`, `data_collection` and `completion_code`.
In the `assets` folder are stored `.js` and `.css` files required for bootstrap and others.
You may change the data path. By default it is stored in a `.json` file, with the following format:
```json
[
    {
        "id": "1",
        "text": "Ciao, tutto bene molto lavoro il questi ultimi giorni. ",
        "highlight_positive": [
            "tutto bene"
        ],
        "highlight_negative": [],
        "id_narrative": "anything"
    },
]
```
The field `id` should be a unique string for each item.
The field `text` can be any string
The fields `highlight_positive` and  `highlight_negative` must be present in the `text` field. They are later shown with a highlighted color in the webUI.

The `blacklist` file constains a `.json` file where blacklisted IDs are stored. Blacklisted ID are ignored from the dataset file and they are not stored in the DB and will not be shown to the users.

`batch_size` and `num_batches` are to decide the size of the batch assigned to each user and the maximum number of batches. Batches are made oup of mutually exclusive narratives, with the exception of the first one, which is shared across narratives. 
More precisely the steps performed to create batches are:
- blacklisted data is removed
- narratives are inserted in the DB
- narratives are sorted by length. The shortest is used as shared narrative across all batches
- `num_batches` are created by stratification on narrative length
- all narratives that are left over, are not assigned to any batch and they will be never show to any user.
- once a user logs in, he is assigned a batch to complete
- data is retrieved real time, before final completion
- if the user refreshes their page, as long as they input the same prolific ID they are able to continue from where they left
- The completion code is shown.
- If the complection code is not provided in the config file, a random 10 characted completion code is generated. This code is unique for each user. 

# Dataset

a copy of the complete dataset is found in `output_dataset`
# Description of the folders

```bash
data/* # contains the raw input dataset
answers/ # contains the crowdsourced data
    └──/data_analysis/ # contains the notebooks with the data analysis
    └──/post_processing/ # contains post processing scripts that were used
    └──/test_set/ # contains the test set data that was gathered
    └──/train_set/ # contains the train set data that was gathered
db/* # contains the DB sqlite files 
    └──/train_set/ # train set
    └──/test_set/ # test set
output_dataset/ # contains the outputdataset
UI/ # contains the ui that was used for crowsourcing
backend_server.py # backend for the crowdsourcing 
server.py # API 
db_utils.py # utilities for sqlite
blacklist.json # files to skip
config.toml # configuration for crowdsourcing
environment.yml # generator for env in conda
```